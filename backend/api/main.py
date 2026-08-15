"""KUBERA API entrypoint.

Run locally:  uvicorn --app-dir backend api.main:app --reload
"""

import logging
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from analysis.benchmark import compare
from analysis.portfolio import summarize, win_loss
from api.chat import run_chat_turn
from api.llm import LLMError, build_provider
from api.tools import ToolArgumentError, ToolContext, ToolError, registry
from backtest.ledger import list_runs
from data.alpaca import AlpacaClient, AlpacaError
from data.db import make_engine, make_session_factory
from data.fred import FredClient, FredError
from data.history import equity_history
from data.market_data import MarketDataClient, MarketDataError
from data.models import ChatMessage
from settings import ConfigError, KuberaSettings, env_file_llm_provider, get_settings

VERSION = "0.1.0"

log = logging.getLogger("kubera.api")


@asynccontextmanager
async def _lifespan(_: FastAPI):
    """Every server boot announces its brain (I014 postmortem: the owner's .env
    said claude-sdk while the running process used openai — OS env vars beat
    .env, and nothing said so). The startup log now makes the mismatch loud."""
    s = get_settings()
    log.info("KUBERA brain: llm_provider=%s (%d tools registered)",
             s.llm_provider, len(registry.names()))
    intended = env_file_llm_provider()
    if intended and intended != s.llm_provider:
        log.warning(
            "PROVIDER MISMATCH: .env says LLM_PROVIDER=%s but this server "
            "resolved %r — an OS environment variable is overriding your .env "
            "(real env vars win). Diagnose: python scripts/brain_check.py",
            intended, s.llm_provider,
        )
    yield


app = FastAPI(title="KUBERA API", version=VERSION, lifespan=_lifespan)

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


@app.get("/", include_in_schema=False)
def orb():
    """The KUBERA Orb — voice-first web interface (T073)."""
    from pathlib import Path

    from fastapi.responses import FileResponse, PlainTextResponse
    page = Path(__file__).resolve().parents[2] / "apps" / "web" / "orb.html"
    if not page.exists():
        return PlainTextResponse("Orb UI missing: apps/web/orb.html", status_code=404)
    return FileResponse(page, media_type="text/html")


@app.get("/api/tts")
async def tts(text: str, voice: str = "en-US-AndrewNeural"):
    """Stream neural speech (MP3) for the Orb. Needs `pip install edge-tts` in the
    server venv — 503 with instructions otherwise."""
    from fastapi.responses import StreamingResponse
    try:
        import edge_tts  # noqa: PLC0415 - optional dependency, lazy on purpose
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="TTS needs edge-tts in the SERVER venv: pip install edge-tts",
        )
    text = text.strip()[:2000]
    if not text:
        raise HTTPException(status_code=422, detail="empty text")

    async def stream():
        communicate = edge_tts.Communicate(text, voice)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                yield chunk["data"]

    return StreamingResponse(stream(), media_type="audio/mpeg")


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
        # I011 diagnostics: which brain, and how many tools it SHOULD see
        "llm_provider": s.llm_provider,
        "tools_registered": len(registry.names()),
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
def market_latest(
    symbol: str,
    client: MarketDataClient = Depends(get_market_client),
    alpaca: AlpacaClient = Depends(get_alpaca_client),
) -> dict:
    """Latest trade + quote with a session-aware freshness verdict (T036b)."""
    try:
        return registry.execute("get_latest", {"symbol": symbol},
                                ToolContext(market=client, alpaca=alpaca))
    except MarketDataError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except (ToolError, ToolArgumentError) as e:
        raise HTTPException(status_code=422, detail=str(e))


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


@app.get("/api/regime/{symbol}")
def symbol_regime(
    symbol: str,
    days: int = 250,
    market: MarketDataClient = Depends(get_market_client),
) -> dict:
    """What kind of market is this symbol in? — via the same tool the chat layer uses."""
    try:
        return registry.execute(
            "get_regime", {"symbol": symbol, "days": days}, ToolContext(market=market)
        )
    except ToolError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except MarketDataError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/levels/{symbol}")
def symbol_levels(
    symbol: str,
    days: int = 250,
    market: MarketDataClient = Depends(get_market_client),
) -> dict:
    """Where are support and resistance? — via the same tool the chat layer uses."""
    try:
        return registry.execute(
            "get_levels", {"symbol": symbol, "days": days}, ToolContext(market=market)
        )
    except ToolError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except MarketDataError as e:
        raise HTTPException(status_code=502, detail=str(e))


def get_fred_client(s: KuberaSettings = Depends(get_settings)):
    """Yield a FRED client, or 503 with an actionable message if unconfigured."""
    try:
        client = FredClient(settings=s)
    except ConfigError as e:
        raise HTTPException(status_code=503, detail=str(e))
    try:
        yield client
    finally:
        client.close()


@app.get("/api/macro")
def macro_context(fred: FredClient = Depends(get_fred_client)) -> dict:
    """Yield curve, VIX, real rates — the macro weather, via the chat layer's tool."""
    try:
        return registry.execute("get_macro_context", {}, ToolContext(fred=fred))
    except ToolError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except FredError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/brief")
def brief(
    type: str = "morning",
    alpaca: AlpacaClient = Depends(get_alpaca_client),
    market: MarketDataClient = Depends(get_market_client),
    session=Depends(get_db_session),
) -> dict:
    """Morning brief / EOD report / weekly review — via the chat layer's tool."""
    fred = None
    try:
        fred = FredClient(settings=get_settings())  # optional: enriches morning brief
    except ConfigError:
        pass  # no FRED key: the event section degrades to a note (T062b)
    try:
        return registry.execute(
            "get_brief", {"type": type},
            ToolContext(alpaca=alpaca, market=market, db=session, fred=fred),
        )
    except (ToolArgumentError, ToolError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    except (AlpacaError, MarketDataError) as e:
        raise HTTPException(status_code=502, detail=str(e))
    finally:
        if fred is not None:
            fred.close()


@app.get("/api/journal")
def journal(
    limit: int = 20,
    market: MarketDataClient = Depends(get_market_client),
    session=Depends(get_db_session),
) -> dict:
    """The decision journal: every recommendation, follow/override, calibration."""
    try:
        return registry.execute(
            "get_journal", {"limit": limit},
            ToolContext(market=market, db=session),
        )
    except ToolError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except MarketDataError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/size/{symbol}")
def size_position(
    symbol: str,
    alpaca: AlpacaClient = Depends(get_alpaca_client),
    market: MarketDataClient = Depends(get_market_client),
    session=Depends(get_db_session),
) -> dict:
    """How many shares would the risk rails allow right now? Every input shown."""
    try:
        return registry.execute(
            "size_position", {"symbol": symbol},
            ToolContext(alpaca=alpaca, market=market, db=session),
        )
    except ToolError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except (AlpacaError, MarketDataError) as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/attribution")
def attribution(session=Depends(get_db_session)) -> dict:
    """Realized P&L by regime, router leg, and entry time — from real fills."""
    try:
        return registry.execute("get_attribution", {}, ToolContext(db=session))
    except ToolError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.get("/api/risk")
def risk_status(
    alpaca: AlpacaClient = Depends(get_alpaca_client),
    session=Depends(get_db_session),
) -> dict:
    """Loss budget, risk tier, breaker state, and Decision Quality Score."""
    try:
        return registry.execute(
            "get_risk_status", {}, ToolContext(alpaca=alpaca, db=session)
        )
    except ToolError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except AlpacaError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/expected-move/{symbol}")
def symbol_expected_move(
    symbol: str,
    horizon_days: int = 5,
    days: int = 420,
    market: MarketDataClient = Depends(get_market_client),
) -> dict:
    """How far does this thing usually travel in N days? Ranges, never targets."""
    try:
        return registry.execute(
            "get_expected_move",
            {"symbol": symbol, "horizon_days": horizon_days, "days": days},
            ToolContext(market=market),
        )
    except ToolError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except MarketDataError as e:
        raise HTTPException(status_code=502, detail=str(e))


class WatchlistAddRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=10)
    note: str | None = Field(default=None, max_length=300)


@app.get("/api/watchlist")
def watchlist_ranked(
    market: MarketDataClient = Depends(get_market_client),
    db=Depends(get_db_session),
) -> dict:
    """T068: the research watchlist, ranked cross-sectionally."""
    try:
        return registry.execute("get_watchlist", {},
                                ToolContext(market=market, db=db))
    except (ToolError, ToolArgumentError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    except MarketDataError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/api/watchlist")
def watchlist_add(req: WatchlistAddRequest, db=Depends(get_db_session)) -> dict:
    try:
        return registry.execute(
            "update_watchlist",
            {"action": "add", "symbol": req.symbol, "note": req.note},
            ToolContext(db=db),
        )
    except (ToolError, ToolArgumentError) as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.delete("/api/watchlist/{symbol}")
def watchlist_remove(symbol: str, db=Depends(get_db_session)) -> dict:
    try:
        return registry.execute(
            "update_watchlist", {"action": "remove", "symbol": symbol},
            ToolContext(db=db),
        )
    except (ToolError, ToolArgumentError) as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.get("/api/execution-quality")
def execution_quality(days: int = 90, session=Depends(get_db_session)) -> dict:
    """T088: implementation shortfall by time-of-day, from real fills."""
    try:
        return registry.execute("get_execution_quality", {"days": days},
                                ToolContext(db=session))
    except (ToolError, ToolArgumentError) as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.get("/api/portfolio-risk")
def portfolio_risk_endpoint(
    days: int = 130,
    alpaca: AlpacaClient = Depends(get_alpaca_client),
    market: MarketDataClient = Depends(get_market_client),
) -> dict:
    """T093: the book's joint risk — vol, contributions, effective bets."""
    try:
        return registry.execute("get_portfolio_risk", {"days": days},
                                ToolContext(alpaca=alpaca, market=market))
    except (ToolError, ToolArgumentError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    except (MarketDataError, AlpacaError) as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/liquidity/{symbol}")
def symbol_liquidity(
    symbol: str,
    market: MarketDataClient = Depends(get_market_client),
) -> dict:
    """T090: spread cost + ADV participation cap, via the chat tool."""
    try:
        return registry.execute("get_liquidity", {"symbol": symbol},
                                ToolContext(market=market))
    except (ToolError, ToolArgumentError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    except MarketDataError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/correlation")
def portfolio_correlation(
    candidate: str | None = None,
    days: int = 130,
    alpaca: AlpacaClient = Depends(get_alpaca_client),
    market: MarketDataClient = Depends(get_market_client),
) -> dict:
    """Overlap guard (T079): holdings correlation matrix + betas, via the chat tool."""
    try:
        return registry.execute(
            "get_correlation", {"candidate": candidate, "days": days},
            ToolContext(alpaca=alpaca, market=market),
        )
    except (ToolError, ToolArgumentError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    except (MarketDataError, AlpacaError) as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/news")
def market_news(
    symbols: str | None = None,
    limit: int = 8,
    market: MarketDataClient = Depends(get_market_client),
) -> dict:
    """Recent headlines (D022), optionally ?symbols=SPY,AAPL — via the chat tool."""
    syms = [s.strip() for s in symbols.split(",") if s.strip()] if symbols else None
    try:
        return registry.execute(
            "get_news", {"symbols": syms, "limit": limit}, ToolContext(market=market),
        )
    except (ToolError, ToolArgumentError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    except MarketDataError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/goal-math")
def goal_math_endpoint(start: float = 1000.0, target: float = 1_000_000.0) -> dict:
    """Deterministic goal arithmetic (I012): required CAGR per horizon, FV with
    contributions, years-to-target, daily-compounding reality check."""
    try:
        return registry.execute(
            "goal_math", {"start": start, "target": target}, ToolContext(),
        )
    except (ToolError, ToolArgumentError) as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.get("/api/intraday/{symbol}")
def symbol_intraday(
    symbol: str,
    timeframe: str = "5Min",
    days: int = 9,
    market: MarketDataClient = Depends(get_market_client),
) -> dict:
    """What kind of day is it so far? Session VWAP + intraday RVOL, via the chat tool."""
    try:
        return registry.execute(
            "get_intraday",
            {"symbol": symbol, "timeframe": timeframe, "days": days},
            ToolContext(market=market),
        )
    except ToolError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except MarketDataError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/triage/{symbol}")
def position_triage(
    symbol: str,
    entry_price: float,
    days_held: int | None = None,
    market: MarketDataClient = Depends(get_market_client),
) -> dict:
    """I'm in the trade — hold, exit, or add? Judged against the live exit plan."""
    try:
        return registry.execute(
            "triage_position",
            {"symbol": symbol, "entry_price": entry_price, "days_held": days_held},
            ToolContext(market=market),
        )
    except ToolError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except MarketDataError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/exit-plan/{symbol}")
def symbol_exit_plan(
    symbol: str,
    market: MarketDataClient = Depends(get_market_client),
) -> dict:
    """How long do I hold? Invalidation, target, review horizon — as data."""
    try:
        return registry.execute(
            "get_exit_plan", {"symbol": symbol}, ToolContext(market=market)
        )
    except ToolError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except MarketDataError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/confluence/{symbol}")
def symbol_confluence(
    symbol: str,
    market: MarketDataClient = Depends(get_market_client),
) -> dict:
    """Do the timeframes agree? Daily + hourly regimes + VWAP side, one read."""
    try:
        return registry.execute(
            "get_confluence", {"symbol": symbol}, ToolContext(market=market)
        )
    except ToolError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except MarketDataError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/breakouts/{symbol}")
def symbol_breakouts(
    symbol: str,
    days: int = 250,
    market: MarketDataClient = Depends(get_market_client),
) -> dict:
    """Did it break out, and did the break HOLD? — via the chat layer's tool."""
    try:
        return registry.execute(
            "get_breakouts", {"symbol": symbol, "days": days}, ToolContext(market=market)
        )
    except ToolError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except MarketDataError as e:
        raise HTTPException(status_code=502, detail=str(e))


def get_llm_provider(s: KuberaSettings = Depends(get_settings)):
    """Yield the configured LLM provider, or 503 with an actionable message."""
    try:
        yield build_provider(s)
    except ConfigError as e:
        raise HTTPException(status_code=503, detail=str(e))


class ChatRequest(BaseModel):
    """`conversation_id`: omit (or send 0) to start a new conversation; reuse the id
    from a previous response to continue that thread."""

    message: str = Field(min_length=1, max_length=20000)  # room for an IPS brief (I012)
    conversation_id: int | None = None
    # T043: explicit user confirmation for confirmation-gated tools (future order tools).
    # Comes from YOUR request — the model cannot set this.
    confirm: bool = False
    # Voice-first owner (D015): true = reply will be spoken aloud (no tables/markdown,
    # ear-rounded numbers, concise). A spoken "yes" never sets `confirm` — clients must
    # translate an explicit confirmation gesture into the flag deliberately.
    voice: bool = False

    model_config = {
        "json_schema_extra": {
            "examples": [{"message": "Should I buy more AAPL?"}]
        }
    }


@app.post("/api/chat")
def chat(
    body: ChatRequest,
    session=Depends(get_db_session),
    alpaca: AlpacaClient = Depends(get_alpaca_client),
    market: MarketDataClient = Depends(get_market_client),
    provider=Depends(get_llm_provider),
) -> dict:
    """Talk to KUBERA. Every message and tool call is persisted (spec §2.7)."""
    ctx = ToolContext(alpaca=alpaca, market=market, db=session, confirmed=body.confirm)
    # Swagger's default example for optional ints is 0 — treat it as "new conversation".
    conversation_id = body.conversation_id or None
    try:
        r = run_chat_turn(session, provider, ctx, body.message, conversation_id,
                          voice=body.voice)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except LLMError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except OperationalError:
        raise HTTPException(
            status_code=503,
            detail="database not initialized — run: alembic -c backend/alembic.ini upgrade head",
        )
    return {
        "conversation_id": r.conversation_id,
        "reply": r.reply,
        "tool_calls": r.tool_trail,
        "usage": {"input_tokens": r.input_tokens, "output_tokens": r.output_tokens},
        "stop_reason": r.stop_reason,
        "asof": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/chat/{conversation_id}")
def chat_history(conversation_id: int, session=Depends(get_db_session)) -> dict:
    """Full audit trail of a conversation — who said what, from which data."""
    try:
        rows = session.execute(
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation_id)
            .order_by(ChatMessage.id)
        ).scalars().all()
    except OperationalError:
        raise HTTPException(status_code=503, detail="database not initialized")
    if not rows:
        raise HTTPException(status_code=404, detail=f"no conversation {conversation_id}")
    return {
        "conversation_id": conversation_id,
        "messages": [
            {
                "role": r.role, "content": r.content, "tool_name": r.tool_name,
                "tool_calls": r.tool_calls_json, "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ],
    }


@app.get("/api/ips")
def investment_policy(session=Depends(get_db_session)) -> dict:
    """The owner's Investment Policy Statement. Updates happen conversationally via the
    confirmation-gated update_ips tool — changing your rules should be deliberate."""
    from data.ips import get_ips as _get
    from data.ips import ips_as_dict as _asdict
    try:
        row = _get(session)
    except OperationalError:
        raise HTTPException(status_code=503, detail="database not initialized")
    if row is None:
        raise HTTPException(status_code=404,
                            detail="No IPS set yet — ask KUBERA to record one in chat.")
    return _asdict(row)


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
