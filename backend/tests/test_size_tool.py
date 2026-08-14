"""size_position tool (T085) — the sizer by voice, every path hand-computed:
clean sizing, cap binding, tier halving, tier-3 pause, breaker block, headroom."""

from datetime import datetime, timezone

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from test_alpaca import paper_settings
from test_paper_loop import BARS_JSON, account_json, position_json

from api.main import app
from api.tools import ToolContext, ToolError, registry
from data.alpaca import AlpacaClient
from data.market_data import MarketDataClient
from data.models import Base
from risk.engine import RiskEngine
from risk.persistence import persist_risk_state


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
    engine.dispose()


def route(equity=100_000.0, positions=None, price=179.0, bars=None):
    def handler(request: httpx.Request) -> httpx.Response:
        p = request.url.path
        if "/v2/account" in p:
            return httpx.Response(200, json=account_json(equity))
        if "/v2/positions" in p:
            return httpx.Response(200, json=positions or [])
        if "/trades/latest" in p:
            return httpx.Response(200, json={
                "symbol": "SPY",
                "trade": {"t": datetime.now(timezone.utc).isoformat(),
                          "p": price, "s": 1}})
        if "/bars" in p:
            return httpx.Response(200, json=bars or BARS_JSON)
        return httpx.Response(404, json={})
    return handler


def run_tool(db, handler):
    transport = httpx.MockTransport(handler)
    with AlpacaClient(settings=paper_settings(), transport=transport) as alpaca, \
         MarketDataClient(settings=paper_settings(), transport=transport) as market:
        return registry.execute("size_position", {"symbol": "SPY"},
                                ToolContext(alpaca=alpaca, market=market, db=db))


def _seed_day(db, start=100_000.0, crash_to=None):
    risk = RiskEngine()
    today = datetime.now(timezone.utc).date().isoformat()
    risk.start_day(start, today)
    if crash_to is not None:
        risk.record_equity(crash_to, datetime.now(timezone.utc))
    persist_risk_state(db, risk)


def test_clean_sizing_cap_binds(db):
    # ATR 2.0 (fixture), price 179: risk 1000$/stop 4 -> 250 sh = 44,750 notional;
    # cap 20% of 100k = 20,000 with no position -> the CAP binds -> 111.732 sh
    out = run_tool(db, route())
    assert out["qty"] == pytest.approx(20_000 / 179.0, abs=1e-3)
    assert out["binding"] == "position_cap" and out["blocked_reason"] is None
    i = out["inputs"]
    assert i["atr"] == pytest.approx(2.0)
    assert i["stop_price"] == pytest.approx(175.0)
    assert i["risk_notional"] == pytest.approx(44_750.0)
    assert i["cap_headroom"] == pytest.approx(20_000.0)
    assert i["price_stale"] is False and i["tier"] is None


def test_tier2_halves_the_risk_leg(db):
    _seed_day(db, 100_000.0)
    out = run_tool(db, route(equity=98_500.0))  # 50% of budget -> tier 2
    # risk leg: 985/4 = 246.25 sh = 44,078.75 * 0.5 = 22,039.69; cap 19,700 binds
    assert out["inputs"]["tier"] == {"level": 2, "name": "half_size", "multiplier": 0.5}
    assert out["qty"] == pytest.approx(19_700 / 179.0, abs=1e-3)
    assert out["binding"] == "position_cap"


def test_tier3_pauses_entries(db):
    _seed_day(db, 100_000.0)
    out = run_tool(db, route(equity=97_700.0))  # 76.7% -> tier 3
    assert out["qty"] == 0.0 and out["binding"] == "blocked"
    assert "entries paused" in out["blocked_reason"]


def test_breaker_blocks_sizing(db):
    _seed_day(db, 100_000.0, crash_to=96_000.0)  # 4% loss trips the breaker
    out = run_tool(db, route(equity=96_000.0))
    assert out["qty"] == 0.0
    assert "circuit breaker" in out["blocked_reason"]
    assert out["inputs"]["breaker_tripped"] is True


def test_existing_position_eats_headroom(db):
    out = run_tool(db, route(
        positions=[position_json(qty=83.8, market_value=15_000.0)]))
    # headroom = 20,000 - 15,000 = 5,000 -> 27.933 sh
    assert out["inputs"]["cap_headroom"] == pytest.approx(5_000.0)
    assert out["qty"] == pytest.approx(5_000 / 179.0, abs=1e-3)


def test_thin_history_refuses_to_size(db):
    thin = {"symbol": "SPY", "next_page_token": None,
            "bars": BARS_JSON["bars"][:5]}
    with pytest.raises(ToolError, match="ATR"):
        run_tool(db, route(bars=thin))


def test_size_endpoint(db):
    from fastapi.testclient import TestClient

    from api import main as main_module

    handler = route()

    def fake_alpaca():
        with AlpacaClient(settings=paper_settings(),
                          transport=httpx.MockTransport(handler)) as a:
            yield a

    def fake_market():
        with MarketDataClient(settings=paper_settings(),
                              transport=httpx.MockTransport(handler)) as m:
            yield m

    app.dependency_overrides[main_module.get_alpaca_client] = fake_alpaca
    app.dependency_overrides[main_module.get_market_client] = fake_market
    app.dependency_overrides[main_module.get_db_session] = lambda: db
    try:
        r = TestClient(app).get("/api/size/SPY")
    finally:
        app.dependency_overrides.pop(main_module.get_alpaca_client)
        app.dependency_overrides.pop(main_module.get_market_client)
        app.dependency_overrides.pop(main_module.get_db_session)
    assert r.status_code == 200
    assert r.json()["qty"] > 0
