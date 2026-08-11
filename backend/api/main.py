"""KUBERA API entrypoint.

Run locally:  uvicorn --app-dir backend api.main:app --reload
"""

from dataclasses import asdict
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.exc import OperationalError

from analysis.benchmark import compare
from analysis.portfolio import summarize, win_loss
from api.tools import ToolArgumentError, ToolContext, ToolError, registry
from backtest.ledger import list_runs
from data.alpaca import AlpacaClient, AlpacaError
from data.db import make_engine, make_session_factory
from data.history import equity_history
from data.market_data import MarketDataClient, MarketDataError
from settings import ConfigError, KuberaSettings, get_settings

VERSION = "0.1.0"

app = FastAPI(title="KUBERA API", version=VERSION)

_engine = None


def get_db_session():
    """Yield a DB session against the configured database (lazy singleton engine)."""
    global _engine
    if _engine is None:
        _engine = make_engine()
    with make_session_factory(_engine)() as session:
        yield session


def get_alpaca_client(s: KuberaSettings = Depends(get_settings)):
    """Yield a paper-account client, or 503 with an actionable message if unconfigured."""
    try:
        client = AlpacaClient(settings=s)
    except ConfigError as e:
        raise HTTPException(status_code=503, detail=str(e))
    try:
        yield client
    finally:
        client.close()


@app.get("/health")
def health() -> dict:
    """Liveness check. Every KUBERA payload is timestamped (AGENTS.md: no undated data)."""
    s = get_settings()
    return {
        "status": "ok",
        "service": "kubera-api",
        "version": VERSION,
        "time": datetime.now(timezone.utc).isoformat(),
        # Config state only — never config values.
        "alpaca_configured": s.alpaca_configured,
        "paper_mode": s.alpaca_paper,
    }


@app.get("/api/tools")
def list_tools() -> dict:
    """The spec §3 tool registry — what the Phase 4 conversation layer will call."""
    return {"tools": registry.schemas(), "count": len(registry.names())}


@app.get("/api/account")
def account(client: AlpacaClient = Depends(get_alpaca_client)) -> dict:
    """Live paper-account snapshot — equity, cash, buying power, timestamped."""
    try:
        return asdict(client.get_account())
    except AlpacaError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/portfolio")
def portfolio(client: AlpacaClient = Depends(get_alpaca_client)) -> dict:
    """Phase 1 exit criterion: what do I hold and what's it worth — live, computed, dated.

    Positions and account state are fetched from the broker at request time (never a stale
    cache presented as current); totals come from the tested analysis layer.
    """
    try:
        acct = client.get_account()
        positions = client.get_positions()
    except AlpacaError as e:
        raise HTTPException(status_code=502, detail=str(e))
    summary = summarize(positions)
    return {
        "account": asdict(acct),
        "summary": {
            "total_market_value": summary.total_market_value,
            "total_cost_basis": summary.total_cost_basis,
            "total_unrealized_pl": summary.total_unrealized_pl,
            "total_return_frac": summary.total_return_frac,
        },
        "win_loss": asdict(win_loss(positions)),
        "positions": [asdict(v) for v in summary.positions],
        "asof": acct.asof.isoformat(),
        "source": acct.source,
    }


def get_market_client(s: KuberaSettings = Depends(get_settings)):
    """Yield a market-data client, or 503 with an actionable message if unconfigured."""
    try:
        client = MarketDataClient(settings=s)
    except ConfigError as e:
        raise HTTPException(status_code=503, detail=str(e))
    try:
        yield client
    finally:
        client.close()


@app.get("/api/market/{symbol}/latest")
def market_latest(symbol: str, client: MarketDataClient = Depends(get_market_client)) -> dict:
    """Latest trade + level-1 quote, each with exchange and fetch timestamps."""
    try:
        return {
            "trade": asdict(client.get_latest_trade(symbol)),
            "quote": asdict(client.get_latest_quote(symbol)),
        }
    except MarketDataError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/market/{symbol}/bars")
def market_bars(
    symbol: str,
    days: int = 30,
    client: MarketDataClient = Depends(get_market_client),
) -> dict:
    """Daily OHLCV history (split-adjusted, free IEX feed)."""
    try:
        return asdict(client.get_daily_bars(symbol, days=days))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except MarketDataError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/briefing/{symbol}")
def symbol_briefing(
    symbol: str,
    days: int = 400,
    alpaca: AlpacaClient = Depends(get_alpaca_client),
    market: MarketDataClient = Depends(get_market_client),
) -> dict:
    """Evidence pack for 'should I buy X' — via the same tool the conversation layer uses."""
    try:
        return registry.execute(
            "get_symbol_briefing",
            {"symbol": symbol, "days": days},
            ToolContext(alpaca=alpaca, market=market),
        )
    except ToolError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except (AlpacaError, MarketDataError) as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/backtests")
def backtests(
    strategy: str | None = None,
    symbol: str | None = None,
    limit: int = 50,
    session=Depends(get_db_session),
) -> dict:
    """The results ledger — every recorded backtest, newest first."""
    try:
        rows = list_runs(session, strategy=strategy, symbol=symbol, limit=limit)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except OperationalError:
        raise HTTPException(
            status_code=503,
            detail="database not initialized — run: alembic -c backend/alembic.ini upgrade head",
        )
    return {
        "count": len(rows),
        "runs": [
            {
                "id": r.id, "ts": r.ts.isoformat(), "strategy": r.strategy,
                "params": r.params_json, "symbol": r.symbol,
                "period": f"{r.start_date} → {r.end_date}", "bars": r.bars_count,
                "cost_bps": r.cost_bps, "cumulative_return": r.cumulative_return,
                "volatility_ann": r.volatility_ann, "sharpe_ann": r.sharpe_ann,
                "max_drawdown_frac": r.max_drawdown_frac,
                "n_rebalances": r.n_rebalances, "source": r.source,
            }
            for r in rows
        ],
    }


@app.post("/api/backtests/run")
def backtests_run(
    strategy: str,
    symbol: str = "SPY",
    days: int = 730,
    cost_bps: float = 5.0,
    session=Depends(get_db_session),
    market: MarketDataClient = Depends(get_market_client),
) -> dict:
    """Run a template backtest on real history and record it — via the registry tool."""
    try:
        return registry.execute(
            "run_backtest",
            {"strategy": strategy, "symbol": symbol, "days": days, "cost_bps": cost_bps},
            ToolContext(db=session, market=market),
        )
    except ToolArgumentError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except OperationalError:
        raise HTTPException(
            status_code=503,
            detail="database not initialized — run: alembic -c backend/alembic.ini upgrade head",
        )
    except MarketDataError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/benchmark")
def benchmark(
    symbol: str = "SPY",
    days: int = 90,
    session=Depends(get_db_session),
    market: MarketDataClient = Depends(get_market_client),
) -> dict:
    """Portfolio equity history vs a benchmark symbol, date-aligned, metrics compared."""
    try:
        portfolio_points = equity_history(session, days=days)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except OperationalError:
        raise HTTPException(
            status_code=503,
            detail="database not initialized — run: alembic -c backend/alembic.ini "
            "upgrade head, then scripts/sync.py to start building history",
        )
    try:
        bars = market.get_daily_bars(symbol, days=days)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except MarketDataError as e:
        raise HTTPException(status_code=502, detail=str(e))
    bench_points = [(b.date, b.close) for b in bars.bars]
    try:
        c = compare(portfolio_points, bench_points)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {
        "symbol": bars.symbol,
        "days": days,
        "dates": c.dates,
        "portfolio_norm": c.portfolio_norm,
        "benchmark_norm": c.benchmark_norm,
        "metrics": {
            "portfolio": asdict(c.portfolio),
            "benchmark": asdict(c.benchmark),
            "excess_return": c.excess_return,
        },
        "asof": bars.asof.isoformat(),
        "source": f"snapshots + {bars.source}",
    }
