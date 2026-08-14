"""Tool registry tests — mechanics, validation, and execution with fake contexts."""

from datetime import datetime, timezone

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel
from test_alpaca import ACCOUNT_JSON, POSITIONS_JSON, paper_settings

from api.main import app
from api.tools import (
    ToolArgumentError,
    ToolContext,
    ToolError,
    ToolRegistry,
    UnknownToolError,
    registry,
)
from data.alpaca import AlpacaClient
from data.db import make_engine, make_session_factory
from data.market_data import MarketDataClient
from data.models import AccountSnapshot, Base, BrokerAccount

client = TestClient(app)


def alpaca_fake() -> AlpacaClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if "/v2/account" in request.url.path:
            return httpx.Response(200, json=ACCOUNT_JSON)
        return httpx.Response(200, json=POSITIONS_JSON)

    return AlpacaClient(settings=paper_settings(), transport=httpx.MockTransport(handler))


def market_fake(bars_json: dict) -> MarketDataClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=bars_json)

    return MarketDataClient(settings=paper_settings(), transport=httpx.MockTransport(handler))


def test_registry_rejects_duplicate_names():
    r = ToolRegistry()

    class A(BaseModel):
        pass

    @r.tool("x", "d", A)
    def h1(ctx, p):
        return {}

    with pytest.raises(ValueError):

        @r.tool("x", "d2", A)
        def h2(ctx, p):
            return {}


def test_schemas_export_shape():
    schemas = registry.schemas()
    assert len(schemas) == len(registry.names()) == 27
    by_name = {s["name"]: s for s in schemas}
    assert "get_portfolio" in by_name
    bars = by_name["get_daily_bars"]
    assert bars["description"]
    assert bars["parameters"]["properties"]["days"]["maximum"] == 3650


def test_unknown_tool():
    with pytest.raises(UnknownToolError) as exc:
        registry.execute("nope", {}, ToolContext())
    assert "available:" in str(exc.value)


def test_invalid_args_rejected():
    with pytest.raises(ToolArgumentError):
        registry.execute("get_daily_bars", {"symbol": "AAPL", "days": 0}, ToolContext())


def test_missing_context_is_clear_error():
    with pytest.raises(ToolError) as exc:
        registry.execute("get_portfolio", {}, ToolContext())
    assert "alpaca" in str(exc.value)


def test_get_portfolio_executes():
    with alpaca_fake() as a:
        out = registry.execute("get_portfolio", {}, ToolContext(alpaca=a))
    assert out["summary"]["total_market_value"] == pytest.approx(1651.00)
    assert out["win_loss"]["winners"] == 1
    assert out["asof"] and out["source"] == "alpaca-paper"


def test_compare_benchmark_executes_end_to_end():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    bars_json = {
        "symbol": "SPY",
        "next_page_token": None,
        "bars": [
            {"t": "2026-08-01T04:00:00Z", "o": 1, "h": 1, "l": 1, "c": 500.0, "v": 1},
            {"t": "2026-08-02T04:00:00Z", "o": 1, "h": 1, "l": 1, "c": 505.0, "v": 1},
        ],
    }
    with make_session_factory(engine)() as s:
        acct = BrokerAccount(broker="alpaca-paper", external_id="A1")
        s.add(acct)
        s.flush()
        for day, equity in ((1, 100000.0), (2, 102000.0)):
            s.add(AccountSnapshot(
                account_id=acct.id, equity=equity, cash=0.0, buying_power=0.0,
                asof=datetime(2026, 8, day, 16, 0, 0, tzinfo=timezone.utc),
                source="alpaca-paper",
            ))
        s.commit()
        with market_fake(bars_json) as m:
            out = registry.execute(
                "compare_benchmark", {"symbol": "SPY", "days": 30},
                ToolContext(db=s, market=m),
            )
    engine.dispose()
    assert out["portfolio"]["cumulative_return"] == pytest.approx(0.02)
    assert out["benchmark"]["cumulative_return"] == pytest.approx(0.01)
    assert out["excess_return"] == pytest.approx(0.01)


def test_api_lists_tools():
    r = client.get("/api/tools")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 27
    assert {t["name"] for t in body["tools"]} == {
        "get_portfolio", "get_latest", "get_daily_bars", "compare_benchmark",
        "get_symbol_briefing", "run_backtest", "get_ips", "update_ips", "get_regime",
        "get_levels", "get_breakouts", "get_intraday", "get_expected_move",
        "get_risk_status", "get_brief", "get_macro_context",
        "record_decision", "mark_decision", "get_journal", "get_confluence",
        "get_exit_plan", "size_position", "triage_position", "get_attribution",
        "goal_math", "get_news", "get_correlation",
    }
