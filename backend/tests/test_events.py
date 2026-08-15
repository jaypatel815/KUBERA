"""T076 event-risk guard — fixed-date hand cases throughout."""

from datetime import date, datetime, timezone

import httpx
import pytest
from test_alpaca import paper_settings
from test_macro import fred_settings
from test_paper_loop import account_json, position_json

from analysis.events import entry_guard, upcoming_events
from data.fred import RELEASES, FredClient

TODAY = date(2026, 8, 14)
CAL = {
    "CPI": ["2026-08-15", "2026-07-15", "2026-09-11"],
    "Employment Situation": ["2026-09-04", "2026-08-07"],
}


# --- pure date math -----------------------------------------------------------

def test_upcoming_events_horizon_and_order():
    evs = upcoming_events(CAL, TODAY, horizon_days=14)
    assert [(e.name, e.date, e.days_away) for e in evs] == [
        ("CPI", "2026-08-15", 1),
    ]  # July is past, September is beyond 14 days... except 09-04 wait
    evs30 = upcoming_events(CAL, TODAY, horizon_days=30)
    assert [(e.name, e.days_away) for e in evs30] == [
        ("CPI", 1), ("Employment Situation", 21), ("CPI", 28),
    ]


def test_entry_guard_window_semantics():
    # release tomorrow, window 1 -> paused with "tomorrow"
    reasons = entry_guard(CAL, TODAY, window_before=1)
    assert len(reasons) == 1 and "tomorrow" in reasons[0] and "CPI" in reasons[0]
    # release day itself -> "today"
    assert "today" in entry_guard(CAL, date(2026, 8, 15), window_before=1)[0]
    # two days out, window 1 -> clear
    assert entry_guard(CAL, date(2026, 8, 13), window_before=1) == []
    # window 0: only the release day pauses
    assert entry_guard(CAL, TODAY, window_before=0) == []
    with pytest.raises(ValueError):
        entry_guard(CAL, TODAY, window_before=-1)


# --- FRED release-dates client ------------------------------------------------

RELEASE_JSON = {"release_dates": [
    {"release_id": 10, "date": "2026-09-11"},
    {"release_id": 10, "date": "2026-08-15"},
    {"release_id": 10, "date": "2026-07-15"},
]}


def fred_fake(status=200, body=RELEASE_JSON) -> FredClient:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "/fred/release/dates" in request.url.path
        assert "include_release_dates_with_no_data" in str(request.url)
        return httpx.Response(status, json=body)
    return FredClient(settings=fred_settings(), transport=httpx.MockTransport(handler))


def test_release_dates_parse_and_calendar():
    with fred_fake() as f:
        dates = f.release_dates(10)
        assert dates == ["2026-09-11", "2026-08-15", "2026-07-15"]
        cal = f.release_calendar()
    assert set(cal) == set(RELEASES) == {"CPI", "Employment Situation"}


def test_release_dates_error_is_actionable():
    from data.fred import FredError
    with fred_fake(status=400) as f:
        with pytest.raises(FredError) as exc:
            f.release_dates(10)
    assert "FRED_API_KEY" in str(exc.value)


# --- the loop pauses new entries into the window ------------------------------

def test_paper_loop_pauses_buys_in_event_window(tmp_path):
    from sqlalchemy import create_engine
    from test_paper_loop import BARS_JSON

    from backtest.paper_loop import run_paper_cycle
    from data.alpaca import AlpacaClient
    from data.db import make_session_factory
    from data.market_data import MarketDataClient
    from data.models import Base
    from risk.engine import RiskEngine

    def handler(request: httpx.Request) -> httpx.Response:
        p = request.url.path
        if "/v2/account" in p:
            return httpx.Response(200, json=account_json())
        if "/v2/positions" in p:
            return httpx.Response(200, json=[position_json("SPY", 0)]
                                  if False else [])
        return httpx.Response(200, json=BARS_JSON)

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    transport = httpx.MockTransport(handler)
    today = datetime.now(timezone.utc).date()
    cal = {"CPI": [today.isoformat()]}   # release TODAY -> window active
    with AlpacaClient(settings=paper_settings(), transport=transport) as a, \
         MarketDataClient(settings=paper_settings(), transport=transport) as m, \
         make_session_factory(engine)() as db:
        r = run_paper_cycle(db, a, m, RiskEngine(), lambda closes: 1.0, "SPY",
                            event_dates=cal, event_window_days=1)
    assert r.action == "no_trade"
    assert "event window" in r.detail and "CPI" in r.detail
    assert "sells" not in r.detail.split("event window")[0]  # reason is first-class
    engine.dispose()


def test_paper_loop_trades_when_calendar_clear():
    from sqlalchemy import create_engine
    from test_paper_loop import BARS_JSON

    from backtest.paper_loop import run_paper_cycle
    from data.alpaca import AlpacaClient
    from data.db import make_session_factory
    from data.market_data import MarketDataClient
    from data.models import Base
    from risk.engine import RiskEngine

    posted = []

    def handler(request: httpx.Request) -> httpx.Response:
        p = request.url.path
        if request.method == "POST" and "/v2/orders" in p:
            posted.append(1)
            return httpx.Response(200, json={
                "id": "o1", "symbol": "SPY", "side": "buy", "qty": "5",
                "status": "accepted"})
        if "/v2/account" in p:
            return httpx.Response(200, json=account_json())
        if "/v2/positions" in p:
            return httpx.Response(200, json=[])
        return httpx.Response(200, json=BARS_JSON)

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    transport = httpx.MockTransport(handler)
    cal = {"CPI": ["2030-01-15"]}        # far future -> no pause
    with AlpacaClient(settings=paper_settings(), transport=transport) as a, \
         MarketDataClient(settings=paper_settings(), transport=transport) as m, \
         make_session_factory(engine)() as db:
        r = run_paper_cycle(db, a, m, RiskEngine(), lambda closes: 1.0, "SPY",
                            event_dates=cal, event_window_days=1)
    assert r.action == "ordered" and posted
    engine.dispose()
