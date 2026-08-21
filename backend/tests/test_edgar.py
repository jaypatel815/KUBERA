"""T083b — EdgarClient + real-clock timing. Fixtures mirror the owner's probe
(2026-08-18: columnar submissions arrays, items strings, acceptance stamps).
"""

from datetime import date, datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy import select
from test_paper_loop import db  # noqa: F401

from analysis.event_rates import hint_from_acceptance
from api.tools import ToolContext, registry
from data.edgar import EdgarClient, EdgarError
from data.models import EarningsObserved
from settings import ConfigError, KuberaSettings

TICKER_MAP = {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
              "1": {"cik_str": 789019, "ticker": "MSFT", "title": "Microsoft"}}

# Probe-faithful columnar shape: the 2026-07-30 20:30 UTC acceptance is the
# owner's real sample (16:30 ET = after close).
SUBMISSIONS = {
    "cik": 320193,
    "filings": {"recent": {
        "form":              ["8-K", "10-Q", "8-K", "8-K"],
        "filingDate":        ["2026-07-30", "2026-07-31", "2026-05-02", "2026-01-29"],
        "items":             ["2.02,9.01", "", "5.02", "2.02,9.01"],
        "acceptanceDateTime": ["2026-07-30T20:30:28.000Z", "", "",
                               "2026-01-29T12:15:00.000Z"],
    }},
}


def edgar_settings(**over) -> KuberaSettings:
    base = dict(_env_file=None, edgar_contact="probe@example.com")
    base.update(over)
    return KuberaSettings(**base)


def client_with(map_json=TICKER_MAP, sub_json=SUBMISSIONS,
                sub_status=200) -> EdgarClient:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "probe@example.com" in request.headers["User-Agent"]  # SEC etiquette
        if request.url.path.endswith("/files/company_tickers.json"):
            return httpx.Response(200, json=map_json)
        if "/submissions/" in request.url.path:
            assert request.url.path.endswith("CIK0000320193.json")  # zero-padded
            return httpx.Response(sub_status, json=sub_json)
        return httpx.Response(404, json={})

    return EdgarClient(settings=edgar_settings(),
                       transport=httpx.MockTransport(handler))


def test_missing_contact_is_actionable():
    with pytest.raises(ConfigError, match="EDGAR_CONTACT"):
        EdgarClient(settings=KuberaSettings(_env_file=None, edgar_contact=None))


def test_earnings_history_filters_to_item_202_and_sorts_oldest_first():
    with client_with() as c:
        h = c.earnings_history("aapl")
    assert h.cik == 320193
    assert [f.filing_date.isoformat() for f in h.filings] == \
        ["2026-01-29", "2026-07-30"]                 # 10-Q and 5.02 8-K excluded
    assert h.filings[1].acceptance_utc == datetime(
        2026, 7, 30, 20, 30, 28, tzinfo=timezone.utc)
    assert h.unparsed == []


def test_unknown_ticker_and_refusals_are_named():
    with client_with() as c:
        with pytest.raises(EdgarError, match="not in EDGAR's ticker map"):
            c.cik_for("ZZZZZZ")
    with client_with(sub_status=403) as c:
        with pytest.raises(EdgarError, match="User-Agent"):
            c.earnings_history("AAPL")


def test_bad_filing_date_reported_never_guessed():
    sub = {"filings": {"recent": {
        "form": ["8-K"], "filingDate": ["not-a-date"],
        "items": ["2.02"], "acceptanceDateTime": [""]}}}
    with client_with(sub_json=sub) as c:
        h = c.earnings_history("AAPL")
    assert h.filings == []
    assert "refusing to guess" in h.unparsed[0]["why"]


# ------------------------------------------------ real-clock timing

def test_hint_from_acceptance_owner_sample_is_amc():
    """The owner's probe sample: 20:30:28Z on 2026-07-30 = 16:30 EDT -> amc."""
    assert hint_from_acceptance(
        datetime(2026, 7, 30, 20, 30, 28, tzinfo=timezone.utc)) == "amc"


def test_hint_boundary_and_winter_clock():
    # 20:00Z in JULY = 16:00 EDT -> amc (boundary inclusive).
    assert hint_from_acceptance(
        datetime(2026, 7, 30, 20, 0, tzinfo=timezone.utc)) == "amc"
    # 20:30Z in JANUARY = 15:30 EST -> still IN session -> bmo semantics.
    assert hint_from_acceptance(
        datetime(2026, 1, 29, 20, 30, tzinfo=timezone.utc)) == "bmo"
    # 12:15Z in January = 07:15 EST -> pre-open -> bmo.
    assert hint_from_acceptance(
        datetime(2026, 1, 29, 12, 15, tzinfo=timezone.utc)) == "bmo"


def test_hint_refuses_naive():
    with pytest.raises(ValueError, match="naive"):
        hint_from_acceptance(datetime(2026, 7, 30, 20, 30))


# ------------------------------------------- tool: EDGAR fills the store

def bars_market_for(symbol: str, n: int = 300):
    from test_alpaca import paper_settings

    from data.market_data import MarketDataClient

    start = date.today() - timedelta(days=n + 30)
    bars, d, i = [], start, 0
    while len(bars) < n:
        if d.weekday() < 5:
            bars.append({"t": f"{d.isoformat()}T04:00:00Z", "o": 100.0 + i,
                         "h": 102.0 + i, "l": 99.0 + i, "c": 100.0 + i,
                         "v": 1_000_000})
            i += 1
        d += timedelta(days=1)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"symbol": symbol,
                                         "next_page_token": None, "bars": bars})

    return MarketDataClient(settings=paper_settings(),
                            transport=httpx.MockTransport(handler))


def test_tool_uses_edgar_history_and_stores_it(db):  # noqa: F811
    """Empty store + EDGAR client: four past 8-Ks land in earnings_observed
    with source=sec-edgar and real-clock hints, and rates compute."""
    today = date.today()
    dates = [(today - timedelta(days=40 * (i + 1))) for i in range(4)]
    sub = {"filings": {"recent": {
        "form": ["8-K"] * 4,
        "filingDate": [d.isoformat() for d in dates],
        "items": ["2.02,9.01"] * 4,
        "acceptanceDateTime": [f"{d.isoformat()}T20:30:00.000Z" for d in dates],
    }}}
    with client_with(sub_json=sub) as e, bars_market_for("AAPL") as m:
        out = registry.execute("get_event_base_rates",
                               {"symbol": "AAPL", "years": 2},
                               ToolContext(db=db, market=m, edgar=e))
    assert out["verdict"] == "rates"
    assert out["events_measured"] == 4
    assert "4 earnings 8-Ks" in out["edgar_note"]
    assert out["by_outcome"]["unknown"]["n"] == 4     # EDGAR has no estimates
    assert all(not r["timing_assumed"] for r in out["reactions"])  # real clocks
    rows = db.execute(select(EarningsObserved)).scalars().all()
    assert len(rows) == 4 and all(r.source == "sec-edgar" for r in rows)
    assert all(r.time_hint == "amc" for r in rows)    # 20:30Z summer = 16:30 ET


def test_tool_degrades_when_edgar_fails(db):  # noqa: F811
    from test_earnings_store import ev

    from data.earnings_store import record_events

    today = date.today()
    record_events(db, [ev("AAPL", today - timedelta(days=30 * (i + 2)),
                          hint="bmo", actual=2.0, est=1.0) for i in range(4)])

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={})

    e = EdgarClient(settings=edgar_settings(),
                    transport=httpx.MockTransport(handler))
    with e, bars_market_for("AAPL") as m:
        out = registry.execute("get_event_base_rates", {"symbol": "AAPL"},
                               ToolContext(db=db, market=m, edgar=e))
    assert out["verdict"] == "rates"                  # store still answers
    assert "EDGAR unavailable" in out["edgar_note"]
