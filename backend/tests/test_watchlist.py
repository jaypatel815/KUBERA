"""T068 watchlist ranking — hand-verified cross-sectional math.

Hand computations:
- three symbols, distinct 21-bar returns -> percentile ranks 0 / 0.5 / 1.0
- composite for the winner (rs=1.0, trending_up fit=1.0, payoff score p):
  0.5*1.0 + 0.3*1.0 + 0.2*p
- monotone-up closes: every 5-day move positive -> win_rate 1.0, payoff 2.0
  (no losers -> capped payoff), score min(1, 1*2/2) = 1.0
"""

import math

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from test_alpaca import paper_settings

from analysis.ranking import (
    RS_WINDOWS,
    payoff_context,
    percentile_ranks,
    rank_watchlist,
    window_return,
)
from api.main import app, get_db_session, get_market_client
from api.tools import ToolContext, registry
from data.db import make_session_factory
from data.market_data import MarketDataClient
from data.models import Base
from data.watchlist import add_symbol, list_symbols, remove_symbol

client = TestClient(app)


def geometric(daily: float, n: int, start: float = 100.0) -> list[float]:
    return [start * math.exp(daily * i) for i in range(n)]


# --- pure ranking math --------------------------------------------------------

def test_window_return_hand_case():
    closes = [100.0] * 10 + [110.0]
    assert window_return(closes, 10) == pytest.approx(0.10)
    assert window_return(closes, 30) is None  # too short -> honest None


def test_percentile_ranks_spread_and_ties():
    assert percentile_ranks({"A": 0.1, "B": 0.2, "C": 0.3}) == {
        "A": 0.0, "B": 0.5, "C": 1.0}
    r = percentile_ranks({"A": 0.1, "B": 0.1, "C": 0.3})
    assert r["A"] == r["B"] == pytest.approx(0.25)  # tied: mean of positions
    assert percentile_ranks({"A": None, "B": 0.5})["A"] is None


def test_payoff_context_monotone_up_is_perfect():
    pay = payoff_context(geometric(0.01, 60))
    assert pay["win_rate"] == 1.0
    assert pay["payoff_ratio"] == 2.0     # no losing moves -> capped
    assert pay["score"] == 1.0
    assert payoff_context([100.0] * 30) is None  # <40 bars -> None


def test_rank_watchlist_orders_and_flags():
    closes = {
        "UPP": geometric(0.004, 150),      # strong riser
        "FLT": [100.0] * 150,              # flat
        "DWN": geometric(-0.004, 150),     # decliner
    }
    labels = {"UPP": "trending_up", "FLT": "range_bound", "DWN": "trending_down"}
    ranked = rank_watchlist(closes, labels)
    assert [r.symbol for r in ranked] == ["UPP", "FLT", "DWN"]
    assert ranked[0].flags == ["top"] and ranked[-1].flags == ["bottom"]
    # winner: rs 1.0, fit 1.0, payoff 1.0 -> 0.5+0.3+0.2 = 1.0 exactly
    assert ranked[0].score == pytest.approx(1.0)
    # flat symbol: rs 0.5, fit 0.35, payoff None (win_rate 0 -> score 0)
    assert ranked[1].score == pytest.approx(0.5 * 0.5 + 0.3 * 0.35)
    assert ranked[2].rs_percentile == 0.0


def test_rank_watchlist_short_history_listed_not_scored():
    closes = {"NEW": geometric(0.01, 10), "OLD": geometric(0.001, 150)}
    ranked = rank_watchlist(closes, {"NEW": "unknown", "OLD": "trending_up"})
    assert ranked[0].symbol == "OLD" and ranked[0].score is not None
    assert ranked[-1].symbol == "NEW" and ranked[-1].score is None
    assert "not enough history" in ranked[-1].note


def test_rs_windows_are_month_multiples():
    assert RS_WINDOWS == (21, 63, 126)  # 1/3/6 months per D020


# --- CRUD ---------------------------------------------------------------------

@pytest.fixture()
def db():
    engine = create_engine("sqlite://",
                           connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with make_session_factory(engine)() as s:
        yield s
    engine.dispose()


def test_watchlist_crud_idempotent(db):
    add_symbol(db, "spy", "core index")
    add_symbol(db, "SPY", "updated thesis")     # re-add updates the note
    rows = list_symbols(db)
    assert len(rows) == 1 and rows[0].note == "updated thesis"
    assert remove_symbol(db, "spy") is True
    assert remove_symbol(db, "SPY") is False    # already gone
    with pytest.raises(ValueError):
        add_symbol(db, "  ")


# --- tools + endpoint ---------------------------------------------------------

def bars_for(closes):
    return {"symbol": "X", "next_page_token": None,
            "bars": [{"t": f"2026-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}T04:00:00Z",
                      "o": c, "h": c * 1.01, "l": c * 0.99, "c": c, "v": 1_000_000}
                     for i, c in enumerate(closes)]}


def test_tools_roundtrip_and_ranking(db):
    up, down = geometric(0.004, 150), geometric(-0.004, 150)

    def handler(request: httpx.Request) -> httpx.Response:
        sym = request.url.path.split("/stocks/")[1].split("/")[0]
        return httpx.Response(200, json=bars_for(up if sym == "UPP" else down))

    out = registry.execute("update_watchlist",
                           {"action": "ADD", "symbol": "upp", "note": "leader"},
                           ToolContext(db=db))
    assert out["updated"] and out["symbol"] == "UPP"  # case-normalized both ways
    registry.execute("update_watchlist", {"action": "add", "symbol": "DWN"},
                     ToolContext(db=db))
    with MarketDataClient(settings=paper_settings(),
                          transport=httpx.MockTransport(handler)) as m:
        view = registry.execute("get_watchlist", {}, ToolContext(db=db, market=m))
    assert [r["symbol"] for r in view["ranked"]] == ["UPP", "DWN"]
    assert view["ranked"][0]["note"] == "leader"      # owner's thesis rides along
    assert view["ranked"][0]["flags"] == ["top"]
    # empty after removal -> friendly note, not an error
    registry.execute("update_watchlist", {"action": "remove", "symbol": "UPP"},
                     ToolContext(db=db))
    registry.execute("update_watchlist", {"action": "remove", "symbol": "DWN"},
                     ToolContext(db=db))
    with MarketDataClient(settings=paper_settings(),
                          transport=httpx.MockTransport(handler)) as m2:
        empty = registry.execute("get_watchlist", {}, ToolContext(db=db, market=m2))
    assert empty["ranked"] == [] and "empty" in empty["note"]


def test_watchlist_endpoints():
    engine = create_engine("sqlite://",
                           connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = make_session_factory(engine)
    up = geometric(0.004, 150)

    def db_override():
        with factory() as s:
            yield s

    def market_override():
        m = MarketDataClient(
            settings=paper_settings(),
            transport=httpx.MockTransport(
                lambda r: httpx.Response(200, json=bars_for(up))))
        try:
            yield m
        finally:
            m.close()

    app.dependency_overrides[get_db_session] = db_override
    app.dependency_overrides[get_market_client] = market_override
    try:
        r = client.post("/api/watchlist", json={"symbol": "spy", "note": "core"})
        assert r.status_code == 200 and r.json()["symbol"] == "SPY"
        view = client.get("/api/watchlist")
        assert view.status_code == 200
        assert view.json()["ranked"][0]["symbol"] == "SPY"
        gone = client.delete("/api/watchlist/SPY")
        assert gone.status_code == 200 and gone.json()["updated"] is True
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
