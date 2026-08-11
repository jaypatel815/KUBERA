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
from analysis.portfolio import summarize, win_loss
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
