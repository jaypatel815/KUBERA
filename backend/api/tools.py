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
from sqlalchemy.orm import Session

from analysis.benchmark import compare
from analysis.briefing import PositionContext, build_briefing
from analysis.portfolio import summarize, win_loss
from backtest.ledger import run_and_record
from backtest.strategies import TEMPLATES, build_strategy
from data.alpaca import AlpacaClient
from data.history import equity_history
from data.market_data import MarketDataClient


class ToolError(RuntimeError):
    """Base for tool failures the conversation layer can relay verbatim."""


class UnknownToolError(ToolError):
    pass


class ToolArgumentError(ToolError):
    pass


@dataclass
class ToolContext:
    """What handlers may need. The API layer builds this per request; tests inject fakes."""

    alpaca: AlpacaClient | None = None
    market: MarketDataClient | None = None
    db: Session | None = None

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


@dataclass
class ToolRegistry:
    _tools: dict[str, ToolSpec] = field(default_factory=dict)

    def tool(self, name: str, description: str, params_model: type[BaseModel]):
        """Decorator: register `handler(ctx, params) -> dict` under a unique name."""

        def decorator(handler: Callable[..., dict]):
            if name in self._tools:
                raise ValueError(f"duplicate tool name: {name}")
            self._tools[name] = ToolSpec(name, description, params_model, handler)
            return handler

        return decorator

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
    "timestamps (free IEX feed).",
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
