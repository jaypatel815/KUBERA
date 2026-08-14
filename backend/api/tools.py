"""Tool-calling registry (T024) — the spec §3 contract, in code.

The conversation layer (Phase 4) never computes a financial figure. It calls tools from
this registry; each tool wraps a real function in /backend/analysis or /backend/data,
validates its arguments with a pydantic model, and returns structured, timestamped data.
Adding a capability = one @registry.tool registration next to the function it wraps.

`registry.schemas()` exports name/description/JSON-schema for each tool — the exact shape
LLM function-calling APIs consume (Anthropic/OpenAI/Gemini formats derive directly).
"""

from dataclasses import asdict, dataclass, field
from typing import Any, Callable

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from analysis.benchmark import compare
from analysis.breakout import detect_breakouts
from analysis.briefing import PositionContext, build_briefing
from analysis.expected_move import expected_move
from analysis.intraday import build_session_read
from analysis.levels import find_levels
from analysis.portfolio import summarize, win_loss
from analysis.regime import classify_regime
from backtest.ledger import run_and_record
from backtest.strategies import TEMPLATES, build_strategy
from data.alpaca import AlpacaClient
from data.history import equity_history
from data.ips import get_ips, ips_as_dict, upsert_ips
from data.market_data import MarketDataClient
from data.models import SignalLog
from risk.dqs import score_decisions
from risk.engine import RiskEngine
from risk.persistence import restore_risk_state
from risk.tiers import current_tier


class ToolError(RuntimeError):
    """Base for tool failures the conversation layer can relay verbatim."""


class UnknownToolError(ToolError):
    pass


class ToolArgumentError(ToolError):
    pass


class ConfirmationRequiredError(ToolError):
    """Raised when a tool needs the user's explicit out-of-band confirmation (T043).

    ctx.confirmed comes from the HTTP request body — user-controlled, outside the LLM's
    reach. The model can ask the user to confirm; it can never confirm for them."""


@dataclass
class ToolContext:
    """What handlers may need. The API layer builds this per request; tests inject fakes.

    `confirmed` is set ONLY from the user's HTTP request (ChatRequest.confirm) — it gates
    tools registered with requires_confirmation=True. Never set it from model output."""

    alpaca: AlpacaClient | None = None
    market: MarketDataClient | None = None
    db: Session | None = None
    confirmed: bool = False

    def require(self, attr: str) -> Any:
        value = getattr(self, attr)
        if value is None:
            raise ToolError(f"tool requires '{attr}' but the context does not provide it")
        return value


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    params_model: type[BaseModel]
    handler: Callable[..., dict]
    requires_confirmation: bool = False  # True = user must confirm out-of-band (T043)


@dataclass
class ToolRegistry:
    _tools: dict[str, ToolSpec] = field(default_factory=dict)

    def tool(self, name: str, description: str, params_model: type[BaseModel],
             requires_confirmation: bool = False):
        """Decorator: register `handler(ctx, params) -> dict` under a unique name.
        Set requires_confirmation=True for anything that changes state with money."""

        def decorator(handler: Callable[..., dict]):
            if name in self._tools:
                raise ValueError(f"duplicate tool name: {name}")
            self._tools[name] = ToolSpec(
                name, description, params_model, handler, requires_confirmation
            )
            return handler

        return decorator

    def requires_confirmation(self, name: str) -> bool:
        spec = self._tools.get(name)
        return bool(spec and spec.requires_confirmation)

    def names(self) -> list[str]:
        return sorted(self._tools)

    def schemas(self) -> list[dict]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.params_model.model_json_schema(),
            }
            for t in (self._tools[n] for n in self.names())
        ]

    def execute(self, name: str, args: dict, ctx: ToolContext) -> dict:
        spec = self._tools.get(name)
        if spec is None:
            raise UnknownToolError(f"unknown tool '{name}' — available: {', '.join(self.names())}")
        try:
            params = spec.params_model(**args)
        except ValidationError as e:
            raise ToolArgumentError(f"invalid arguments for '{name}': {e}") from e
        if spec.requires_confirmation and not ctx.confirmed:
            raise ConfirmationRequiredError(
                f"tool '{name}' requires the user's explicit confirmation. Ask the user "
                "to confirm; they must resend their request with confirm=true. You "
                "cannot confirm on their behalf."
            )
        return spec.handler(ctx, params)


registry = ToolRegistry()


# ---------------------------------------------------------------------------- tools


class NoArgs(BaseModel):
    pass


class SymbolArgs(BaseModel):
    symbol: str = Field(min_length=1, max_length=10, description="Ticker, e.g. AAPL")


class BarsArgs(SymbolArgs):
    days: int = Field(default=30, ge=1, le=3650, description="Calendar days of history")


class BenchmarkArgs(BaseModel):
    symbol: str = Field(default="SPY", min_length=1, max_length=10)
    days: int = Field(default=90, ge=2, le=3650)


class BacktestArgs(BaseModel):
    strategy: str = Field(description=f"One of: {', '.join(sorted(TEMPLATES))}")
    symbol: str = Field(default="SPY", min_length=1, max_length=10)
    days: int = Field(default=730, ge=30, le=3650)
    cost_bps: float = Field(default=5.0, ge=0, lt=10_000)


class BriefingArgs(SymbolArgs):
    days: int = Field(
        default=400, ge=30, le=3650,
        description="Calendar days of history to base the briefing on (400 covers 52 weeks)",
    )


@registry.tool(
    "get_portfolio",
    "Live portfolio: account state, positions, totals, win/loss breakdown. All values "
    "fetched from the broker at call time and computed deterministically; timestamped.",
    NoArgs,
)
def _get_portfolio(ctx: ToolContext, _: NoArgs) -> dict:
    client: AlpacaClient = ctx.require("alpaca")
    acct = client.get_account()
    positions = client.get_positions()
    s = summarize(positions)
    return {
        "account": asdict(acct),
        "summary": {
            "total_market_value": s.total_market_value,
            "total_cost_basis": s.total_cost_basis,
            "total_unrealized_pl": s.total_unrealized_pl,
            "total_return_frac": s.total_return_frac,
        },
        "win_loss": asdict(win_loss(positions)),
        "positions": [asdict(v) for v in s.positions],
        "asof": acct.asof.isoformat(),
        "source": acct.source,
    }


@registry.tool(
    "get_latest",
    "Latest trade price and level-1 bid/ask for one symbol, with exchange and fetch "
    "timestamps (free IEX feed). Each payload carries age_seconds and a stale flag "
    "(exchange event older than 15 min — normal outside market hours). NEVER present "
    "stale data as live, and never base a trade recommendation on it without saying "
    "exactly how old it is.",
    SymbolArgs,
)
def _get_latest(ctx: ToolContext, p: SymbolArgs) -> dict:
    market: MarketDataClient = ctx.require("market")
    return {
        "trade": asdict(market.get_latest_trade(p.symbol)),
        "quote": asdict(market.get_latest_quote(p.symbol)),
    }


@registry.tool(
    "get_daily_bars",
    "Daily OHLCV history for one symbol (split-adjusted), oldest first.",
    BarsArgs,
)
def _get_daily_bars(ctx: ToolContext, p: BarsArgs) -> dict:
    market: MarketDataClient = ctx.require("market")
    return asdict(market.get_daily_bars(p.symbol, days=p.days))


def position_context_for(client: AlpacaClient, symbol: str) -> PositionContext | None:
    """Owner's current exposure to `symbol`, or None if not held."""
    positions = client.get_positions()
    match = next((p for p in positions if p.symbol == symbol), None)
    if match is None:
        return None
    total_mv = sum(p.market_value for p in positions)
    return PositionContext(
        qty=match.qty,
        market_value=match.market_value,
        unrealized_pl=match.unrealized_pl,
        portfolio_weight_frac=(match.market_value / total_mv) if total_mv > 0 else None,
    )


@registry.tool(
    "get_symbol_briefing",
    "Evidence pack for 'should I buy X': trailing returns (20/60/252 trading days), "
    "annualized volatility, max drawdown, distance from 52-week high/low, SMA50/200 trend "
    "context, and the user's current exposure. Facts only, dated; fields degrade to null "
    "when history is thin. Narration must state data recency and never present certainty.",
    BriefingArgs,
)
def _get_symbol_briefing(ctx: ToolContext, p: BriefingArgs) -> dict:
    market: MarketDataClient = ctx.require("market")
    bars = market.get_daily_bars(p.symbol, days=p.days)
    if not bars.bars:
        raise ToolError(f"no price history returned for '{p.symbol}' — check the symbol")
    position = None
    if ctx.alpaca is not None:  # exposure context is optional, not required
        position = position_context_for(ctx.alpaca, p.symbol.upper())
    briefing = build_briefing(
        p.symbol,
        [b.close for b in bars.bars],
        [b.date for b in bars.bars],
        position=position,
    )
    return {
        "briefing": asdict(briefing),
        "asof": bars.asof.isoformat(),
        "source": bars.source,
    }


class RegimeArgs(SymbolArgs):
    days: int = Field(
        default=250, ge=40, le=3650,
        description="Calendar days of history (250 gives ~170 bars — enough for a "
                    "meaningful range-width percentile)",
    )


@registry.tool(
    "get_regime",
    "Classify the market regime for one symbol from daily bars: trending_up / "
    "trending_down / range_bound / breakout_watch, with the evidence behind it — "
    "swing structure (higher highs/lows), 20-bar range and its width percentile, "
    "RVOL (relative volume, labeled by feed), range escapes with fakeout suspicion, "
    "and a per-signal confidence checklist. Use it to pick the playbook: trend-follow "
    "in trends, trade edges in ranges, wait in coils — and remember 'no trade today' "
    "is a valid conclusion. Narration must state the as-of date and the feed caveat.",
    RegimeArgs,
)
def _get_regime(ctx: ToolContext, p: RegimeArgs) -> dict:
    market: MarketDataClient = ctx.require("market")
    bars = market.get_daily_bars(p.symbol, days=p.days)
    if len(bars.bars) < 21:
        raise ToolError(
            f"only {len(bars.bars)} daily bars for '{p.symbol}' — need at least 21 "
            "to classify a regime (check the symbol or widen days)"
        )
    reading = classify_regime(
        [b.high for b in bars.bars],
        [b.low for b in bars.bars],
        [b.close for b in bars.bars],
        [b.volume for b in bars.bars],
        [b.date for b in bars.bars],
        volume_feed=bars.source,
    )
    return {
        "symbol": bars.symbol,
        "regime": asdict(reading),
        "asof": bars.asof.isoformat(),
        "source": bars.source,
    }


class LevelsArgs(SymbolArgs):
    days: int = Field(
        default=250, ge=40, le=3650,
        description="Calendar days of history to scan for swing rejections",
    )


@registry.tool(
    "get_levels",
    "Support and resistance levels for one symbol, from clustered swing highs/lows: "
    "each level has a price, touch count (repeated rejections make a level real — "
    "weight 5 touches over 2), kind (support/resistance/mixed provenance), and signed "
    "distance from the last close; plus the nearest support and resistance. Doctrine: "
    "trade the edges of a range, not the middle; an escape through a level needs "
    "volume confirmation (cross-check get_regime). State the as-of date.",
    LevelsArgs,
)
def _get_levels(ctx: ToolContext, p: LevelsArgs) -> dict:
    market: MarketDataClient = ctx.require("market")
    bars = market.get_daily_bars(p.symbol, days=p.days)
    if len(bars.bars) < 20:
        raise ToolError(
            f"only {len(bars.bars)} daily bars for '{p.symbol}' — need at least 20 "
            "to estimate levels (check the symbol or widen days)"
        )
    reading = find_levels(
        [b.high for b in bars.bars],
        [b.low for b in bars.bars],
        [b.close for b in bars.bars],
        [b.date for b in bars.bars],
    )
    return {
        "symbol": bars.symbol,
        "levels": asdict(reading),
        "asof": bars.asof.isoformat(),
        "source": bars.source,
    }


class BreakoutArgs(SymbolArgs):
    days: int = Field(
        default=250, ge=40, le=3650,
        description="Calendar days of history to scan for breakout events",
    )


@registry.tool(
    "get_breakouts",
    "Breakout events for one symbol — the doctrine's full three-part test: fresh "
    "range escape + volume expansion (RVOL at the break) + hold-outside check. Each "
    "event has direction, boundary, status (confirmed / failed=completed fakeout / "
    "unconfirmed=held on weak volume / pending) and how many bars it held. `active` "
    "means the latest break is still live. Never trust an escape without volume; a "
    "'failed' event is the $100->$106->$99 lesson. State the as-of date.",
    BreakoutArgs,
)
def _get_breakouts(ctx: ToolContext, p: BreakoutArgs) -> dict:
    market: MarketDataClient = ctx.require("market")
    bars = market.get_daily_bars(p.symbol, days=p.days)
    if len(bars.bars) < 21:
        raise ToolError(
            f"only {len(bars.bars)} daily bars for '{p.symbol}' — need at least 21 "
            "to scan for breakouts (check the symbol or widen days)"
        )
    scan = detect_breakouts(
        [b.high for b in bars.bars],
        [b.low for b in bars.bars],
        [b.close for b in bars.bars],
        [b.volume for b in bars.bars],
        [b.date for b in bars.bars],
    )
    return {
        "symbol": bars.symbol,
        "breakouts": asdict(scan),
        "volume_feed": bars.source,  # D006: RVOL is relative to this feed only
        "asof": bars.asof.isoformat(),
        "source": bars.source,
    }


class IntradayArgs(SymbolArgs):
    timeframe: str = Field(
        default="5Min", pattern="^(1Min|5Min|15Min|30Min|1Hour)$",
        description="Bar size for the session read",
    )
    days: int = Field(
        default=9, ge=1, le=30,
        description="Calendar days to fetch (9 gives ~5 prior sessions of RVOL context)",
    )


@registry.tool(
    "get_intraday",
    "Today's session read for one symbol: session VWAP with price side and distance, "
    "VWAP crossings (many = churn, no trend — be selective), cumulative volume, and "
    "intraday RVOL — today's volume at this point of the day vs the same point in "
    "prior sessions (the honest 'is the market interested?' measure; IEX-relative, "
    "never absolute, per D006). Regular hours only by default. This is the 'what "
    "kind of day is it so far' companion to get_regime's daily view.",
    IntradayArgs,
)
def _get_intraday(ctx: ToolContext, p: IntradayArgs) -> dict:
    market: MarketDataClient = ctx.require("market")
    bars = market.get_intraday_bars(p.symbol, timeframe=p.timeframe, days=p.days)
    if not bars.bars:
        raise ToolError(
            f"no intraday bars for '{p.symbol}' — check the symbol, or the market "
            "may not have opened yet today"
        )
    try:
        reading = build_session_read(bars.bars, volume_feed=bars.source)
    except ValueError as e:
        raise ToolError(str(e)) from e
    return {
        "symbol": bars.symbol,
        "timeframe": bars.timeframe,
        "intraday": asdict(reading),
        "asof": bars.asof.isoformat(),
        "source": bars.source,
    }


class ExpectedMoveArgs(SymbolArgs):
    horizon_days: int = Field(default=5, ge=1, le=60,
                              description="Holding window in trading days")
    days: int = Field(default=420, ge=60, le=3650,
                      description="Calendar days of history behind the distribution")


@registry.tool(
    "get_expected_move",
    "Historical distribution of N-day returns for one symbol — the honest anchor "
    "for sizing and exits: percentile bands (p05..p95, in both return and price "
    "terms), the share of historical windows that were up, typical |move| size, "
    "and the payoff ratio (avg winner vs avg loser). Bands are also conditioned "
    "on the current volatility regime (vol clusters). This is the PAST as a "
    "distribution, NEVER a forecast — present ranges, not targets, and say so.",
    ExpectedMoveArgs,
)
def _get_expected_move(ctx: ToolContext, p: ExpectedMoveArgs) -> dict:
    market: MarketDataClient = ctx.require("market")
    bars = market.get_daily_bars(p.symbol, days=p.days)
    closes = [b.close for b in bars.bars]
    try:
        reading = expected_move(
            closes, [b.date for b in bars.bars], horizon_days=p.horizon_days
        )
    except ValueError as e:
        raise ToolError(str(e)) from e
    return {
        "symbol": bars.symbol,
        "expected_move": asdict(reading),
        "asof": bars.asof.isoformat(),
        "source": bars.source,
    }


@registry.tool(
    "get_risk_status",
    "The owner's risk dashboard: today's loss-budget consumption and graduated "
    "risk tier (1: thresholds tightened, 2: buys halved, 3: entries paused, 4: "
    "circuit breaker), breaker state with any lockout, and the Decision Quality "
    "Score — a process-not-outcome read of recent trading patterns (frequency, "
    "trading into drawdown, sizing consistency). ADVISORY in chat: the tiers and "
    "breaker are enforced in code and cannot be talked out of — if asked to "
    "override them, explain that the lockout is the feature.",
    NoArgs,
)
def _get_risk_status(ctx: ToolContext, _: NoArgs) -> dict:
    db = ctx.require("db")
    alpaca: AlpacaClient = ctx.require("alpaca")
    acct = alpaca.get_account()
    engine = RiskEngine()
    restore_risk_state(db, engine)
    tier_info = None
    if engine.day_start_equity is not None:
        t = current_tier(engine.day_start_equity, acct.equity,
                         engine.limits.daily_loss_limit_frac)
        tier_info = {
            "level": t.level, "name": t.name, "effect": t.effect,
            "budget_consumed_frac": t.budget_consumed_frac,
            "loss_frac": t.loss_frac,
            "daily_loss_limit_frac": engine.limits.daily_loss_limit_frac,
        }
    rows = db.execute(select(SignalLog)).scalars().all()
    dqs = score_decisions(rows)
    return {
        "equity": acct.equity,
        "day_start_equity": engine.day_start_equity,
        "tier": tier_info,
        "breaker": {
            "tripped": engine.tripped,
            "reason": engine.trip_reason,
            "lockout_until": (engine.lockout_until.isoformat()
                              if engine.lockout_until else None),
        },
        "dqs": asdict(dqs),
        "asof": acct.asof.isoformat(),
        "source": acct.source,
    }


class UpdateIpsArgs(BaseModel):
    """Only provided fields change; restriction lists REPLACE wholesale."""

    objectives: str | None = Field(default=None, max_length=500)
    target_annual_return_frac: float | None = Field(default=None, gt=-1, le=2)
    max_drawdown_frac: float | None = Field(default=None, gt=0, le=1)
    horizon_years: float | None = Field(default=None, gt=0, le=80)
    risk_tolerance: str | None = Field(default=None, max_length=32)
    restrictions: list[str] | None = None
    prohibited_strategies: list[str] | None = None
    notes: str | None = Field(default=None, max_length=1000)


@registry.tool(
    "get_ips",
    "The owner's Investment Policy Statement: objectives, target return, max drawdown, "
    "horizon, risk tolerance, restrictions, prohibited strategies. Check every "
    "recommendation against it.",
    NoArgs,
)
def _get_ips(ctx: ToolContext, _: NoArgs) -> dict:
    db = ctx.require("db")
    row = get_ips(db)
    if row is None:
        return {"ips": None,
                "note": "No IPS set yet — offer to record one via update_ips."}
    return {"ips": ips_as_dict(row)}


@registry.tool(
    "update_ips",
    "Update the owner's Investment Policy Statement (partial: only provided fields "
    "change; restriction lists replace wholesale). Changing your own investment rules "
    "is a deliberate act — this tool requires the owner's explicit confirmation.",
    UpdateIpsArgs,
    requires_confirmation=True,
)
def _update_ips(ctx: ToolContext, p: UpdateIpsArgs) -> dict:
    db = ctx.require("db")
    row = upsert_ips(db, **p.model_dump())
    return {"updated": True, "ips": ips_as_dict(row)}


@registry.tool(
    "run_backtest",
    "Backtest a named strategy template on real price history and record the run in the "
    "results ledger. Returns computed metrics (cumulative return, volatility, Sharpe, max "
    "drawdown, rebalances). Backtests describe the PAST — never present them as promises.",
    BacktestArgs,
)
def _run_backtest(ctx: ToolContext, p: BacktestArgs) -> dict:
    db = ctx.require("db")
    market: MarketDataClient = ctx.require("market")
    try:
        strategy = build_strategy(p.strategy)
    except ValueError as e:
        raise ToolArgumentError(str(e)) from e
    result, row = run_and_record(
        db, market, strategy, {"template": p.strategy}, p.symbol,
        days=p.days, cost_bps=p.cost_bps,
    )
    return {
        "run_id": row.id,
        "strategy": result.strategy_name,
        "symbol": row.symbol,
        "period": f"{row.start_date} → {row.end_date}",
        "bars": row.bars_count,
        "cost_bps": p.cost_bps,
        "cumulative_return": result.cumulative_return,
        "volatility_ann": result.volatility_ann,
        "sharpe_ann": result.sharpe_ann,
        "max_drawdown_frac": result.max_drawdown_frac,
        "n_rebalances": result.n_rebalances,
        "recorded_at": row.ts.isoformat(),
        "source": row.source,
    }


@registry.tool(
    "compare_benchmark",
    "Portfolio equity history vs a benchmark symbol: date-aligned normalized curves, "
    "cumulative/vol/Sharpe/drawdown per series, excess return.",
    BenchmarkArgs,
)
def _compare_benchmark(ctx: ToolContext, p: BenchmarkArgs) -> dict:
    db: Session = ctx.require("db")
    market: MarketDataClient = ctx.require("market")
    portfolio_points = equity_history(db, days=p.days)
    bars = market.get_daily_bars(p.symbol, days=p.days)
    c = compare(portfolio_points, [(b.date, b.close) for b in bars.bars])
    return {
        "symbol": bars.symbol,
        "dates": c.dates,
        "portfolio_norm": c.portfolio_norm,
        "benchmark_norm": c.benchmark_norm,
        "portfolio": asdict(c.portfolio),
        "benchmark": asdict(c.benchmark),
        "excess_return": c.excess_return,
        "asof": bars.asof.isoformat(),
        "source": f"snapshots + {bars.source}",
    }
