"""T090 liquidity costs — hand-verified numbers.

Hand computations:
- bid 99.90 / ask 100.10: mid 100.00, spread 0.20 -> 20.0 bps; per-side cost 10.0
- bid 100 / ask 100.01: spread ~1.0 bps -> half is 0.5, exactly at the floor
- ADV of [1M x 25]: 1,000,000; 1% participation cap = 10,000 shares
"""

import httpx
import pytest
from fastapi.testclient import TestClient
from test_alpaca import ACCOUNT_JSON, POSITIONS_JSON, paper_settings
from test_paper_loop import BARS_JSON

from analysis.liquidity import (
    MAX_PARTICIPATION,
    MIN_COST_BPS,
    average_daily_volume,
    estimated_cost_bps,
    liquidity_profile,
    participation_cap_shares,
    spread_bps,
)
from api.main import app, get_market_client
from api.tools import ToolContext, ToolError, registry
from data.alpaca import AlpacaClient
from data.market_data import MarketDataClient

client = TestClient(app)


# --- pure math ----------------------------------------------------------------

def test_spread_bps_hand_computed():
    assert spread_bps(99.90, 100.10) == pytest.approx(20.0)
    assert spread_bps(100.0, 100.0) == 0.0


def test_spread_rejects_bad_quotes():
    with pytest.raises(ValueError):
        spread_bps(0, 100)
    with pytest.raises(ValueError):
        spread_bps(100.10, 99.90)  # crossed


def test_cost_floor():
    # ~1bps spread -> half is ~0.5 = the floor; a wide spread clears it
    assert estimated_cost_bps(spread_bps(100.0, 100.01)) == pytest.approx(MIN_COST_BPS)
    assert estimated_cost_bps(20.0) == pytest.approx(10.0)


def test_adv_and_participation_cap():
    assert average_daily_volume([1_000_000.0] * 25) == pytest.approx(1_000_000)
    # window: only the trailing 20 count
    vols = [9_999_999.0] * 5 + [1_000_000.0] * 20
    assert average_daily_volume(vols) == pytest.approx(1_000_000)
    assert participation_cap_shares(1_000_000) == pytest.approx(10_000)
    assert MAX_PARTICIPATION == 0.01


def test_adv_input_validation():
    with pytest.raises(ValueError):
        average_daily_volume([])
    with pytest.raises(ValueError):
        average_daily_volume([100, -1])


def test_profile_composes():
    prof = liquidity_profile("spy", 99.90, 100.10, [1_000_000.0] * 25,
                             "28s", False)
    assert prof.symbol == "SPY"
    assert prof.spread_bps == pytest.approx(20.0)
    assert prof.estimated_cost_bps == pytest.approx(10.0)
    assert prof.cap_shares == pytest.approx(10_000)
    assert prof.cap_notional == pytest.approx(1_000_000.0)  # 10k * mid 100
    assert "understates" in prof.note  # the IEX honesty label


# --- tool + endpoint ----------------------------------------------------------

QUOTE_JSON = {"quote": {"bp": 99.90, "bs": 10, "ap": 100.10, "as": 12,
                        "t": "2026-08-14T15:00:00Z"}}
NO_QUOTE_JSON = {"quote": {"bp": 0, "bs": 0, "ap": 0, "as": 0,
                           "t": "2026-08-14T15:00:00Z"}}


def market_fake(quote_json=QUOTE_JSON) -> MarketDataClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if "/quotes/latest" in request.url.path:
            return httpx.Response(200, json=quote_json)
        return httpx.Response(200, json=BARS_JSON)
    return MarketDataClient(settings=paper_settings(),
                            transport=httpx.MockTransport(handler))


def test_liquidity_tool_executes():
    with market_fake() as m:
        out = registry.execute("get_liquidity", {"symbol": "spy"},
                               ToolContext(market=m))
    assert out["symbol"] == "SPY"
    assert out["spread_bps"] == pytest.approx(20.0)
    # BARS_JSON volume is uniform 4M -> cap = 40k shares
    assert out["cap_shares"] == pytest.approx(40_000)
    assert out["asof"] and out["source"]


def test_liquidity_tool_refuses_one_sided_quote():
    with market_fake(NO_QUOTE_JSON) as m:
        with pytest.raises(ToolError) as exc:
            registry.execute("get_liquidity", {"symbol": "SPY"},
                             ToolContext(market=m))
    assert "fiction" in str(exc.value)


def test_liquidity_endpoint():
    def market_override():
        m = market_fake()
        try:
            yield m
        finally:
            m.close()

    app.dependency_overrides[get_market_client] = market_override
    try:
        r = client.get("/api/liquidity/SPY")
        assert r.status_code == 200
        assert r.json()["estimated_cost_bps"] == pytest.approx(10.0)
    finally:
        app.dependency_overrides.clear()


# --- ADV cap binds inside size_position (T090 wiring) -------------------------

THIN_BARS = {
    "symbol": "THIN", "next_page_token": None,
    "bars": [
        {"t": f"2026-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}T04:00:00Z",
         "o": 100.0 + i, "h": 101.0 + i, "l": 99.0 + i, "c": 100.0 + i,
         "v": 500}  # ADV 500 -> 1% cap = 5 shares, far below the risk budget
        for i in range(40)
    ],
}
TRADE_JSON = {"trade": {"p": 139.0, "s": 10, "t": "2026-08-14T15:00:00Z"}}


def test_size_position_binds_on_adv_for_thin_symbols():
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if "/v2/account" in path:
            return httpx.Response(200, json=ACCOUNT_JSON)
        if "/v2/positions" in path:
            return httpx.Response(200, json=POSITIONS_JSON)
        if "/trades/latest" in path:
            return httpx.Response(200, json=TRADE_JSON)
        return httpx.Response(200, json=THIN_BARS)

    from sqlalchemy import create_engine

    from data.db import make_session_factory
    from data.models import Base
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    transport = httpx.MockTransport(handler)
    with AlpacaClient(settings=paper_settings(), transport=transport) as a, \
         MarketDataClient(settings=paper_settings(), transport=transport) as m, \
         make_session_factory(engine)() as db:
        out = registry.execute("size_position", {"symbol": "THIN"},
                               ToolContext(alpaca=a, market=m, db=db))
    assert out["binding"] == "adv_cap"
    assert out["qty"] == pytest.approx(5.0)          # 1% of ADV 500
    assert out["inputs"]["adv_shares"] == pytest.approx(500)
    assert "understates" in out["inputs"]["adv_note"]
    engine.dispose()
