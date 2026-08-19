"""T083 (post-probe) — the self-accumulated earnings store + reworked tool.

The owner's probe measured past FMP calendar windows PAYWALLED, so history
comes from earnings_observed rows recorded from the working forward window.
"""

from datetime import date, timedelta

import httpx
import pytest
from sqlalchemy import select
from test_paper_loop import db  # noqa: F401

from api.tools import ToolContext, ToolError, registry
from data.earnings_store import record_calendar, record_events, stored_events
from data.fmp import EarningsEvent
from data.models import EarningsObserved


def ev(symbol: str, d: date, hint: str | None = "amc",
       est: float | None = 1.5, actual: float | None = None) -> EarningsEvent:
    return EarningsEvent(symbol=symbol, date=d, time_hint=hint,
                         eps_estimated=est, revenue_estimated=None,
                         fiscal_ending=None, eps_actual=actual)


def test_record_dedupes_and_backfills_actuals(db):  # noqa: F811
    d = date(2026, 5, 20)
    assert record_events(db, [ev("NVDA", d)]) == 1
    assert record_events(db, [ev("NVDA", d)]) == 0          # duplicate: no-op
    # A later fetch carries the reported figure -> ENRICHES, never duplicates.
    assert record_events(db, [ev("NVDA", d, actual=1.9)]) == 1
    rows = db.execute(select(EarningsObserved)).scalars().all()
    assert len(rows) == 1
    assert rows[0].eps_actual == pytest.approx(1.9)
    assert rows[0].eps_estimated == pytest.approx(1.5)      # original kept


def test_record_calendar_is_best_effort(db):  # noqa: F811
    class Cal:
        events = [ev("AAPL", date(2026, 6, 1))]

    assert record_calendar(db, Cal()) == 1
    assert record_calendar(None, Cal()) == 0                # no db: quiet 0

    class Broken:
        @property
        def events(self):
            raise RuntimeError("boom")

    assert record_calendar(db, Broken()) == 0               # never raises


def test_stored_events_filters_and_orders(db):  # noqa: F811
    record_events(db, [ev("AAPL", date(2026, 6, 1)),
                       ev("AAPL", date(2026, 3, 1)),
                       ev("MSFT", date(2026, 4, 1))])
    got = stored_events(db, "aapl")
    assert [r.event_date for r in got] == ["2026-03-01", "2026-06-01"]


# ------------------------------------------------- tool on the store

def bars_market(n: int = 400):
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

    payload = {"symbol": "AAPL", "next_page_token": None, "bars": bars}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    return MarketDataClient(settings=paper_settings(),
                            transport=httpx.MockTransport(handler))


def test_tool_computes_rates_from_stored_history_without_fmp(db):  # noqa: F811
    """FMP absent entirely: stored observations alone answer, with the note."""
    today = date.today()
    past = [today - timedelta(days=30 * (i + 2)) for i in range(4)]
    record_events(db, [ev("AAPL", d, hint="bmo", actual=2.0, est=1.0)
                       for d in past])
    with bars_market() as m:
        out = registry.execute("get_event_base_rates",
                               {"symbol": "AAPL", "years": 2},
                               ToolContext(db=db, market=m))
    assert out["verdict"] == "rates"
    assert out["events_measured"] == 4
    assert out["by_outcome"]["beat"]["n"] == 4
    assert "self-accumulated" in out["history_source"]
    assert "not configured" in out["fetch_note"]


def test_tool_empty_store_names_the_paywall_reality(db):  # noqa: F811
    with bars_market() as m:
        with pytest.raises(ToolError, match="no observed past earnings dates"):
            registry.execute("get_event_base_rates", {"symbol": "AAPL"},
                             ToolContext(db=db, market=m))


def test_tool_forward_fetch_feeds_the_store(db):  # noqa: F811
    """With FMP present, the forward window is fetched AND recorded — future
    dates land in the store even though they can't be measured yet."""
    from test_fmp import fmp_settings

    from data.fmp import FmpClient

    future = (date.today() + timedelta(days=10)).isoformat()

    def fmp_handler(request: httpx.Request) -> httpx.Response:
        assert "earnings-calendar" in request.url.path
        return httpx.Response(200, json=[
            {"symbol": "AAPL", "date": future, "epsEstimated": 2.5, "time": "amc"}])

    fmp = FmpClient(settings=fmp_settings(),
                    transport=httpx.MockTransport(fmp_handler))
    today = date.today()
    past = [today - timedelta(days=30 * (i + 2)) for i in range(4)]
    record_events(db, [ev("AAPL", d, hint="bmo", actual=1.0, est=2.0)
                       for d in past])

    with bars_market() as m, fmp:
        out = registry.execute("get_event_base_rates", {"symbol": "AAPL"},
                               ToolContext(db=db, market=m, fmp=fmp))
    assert out["by_outcome"]["miss"]["n"] == 4
    assert out["fetch_note"] is None                        # fetch succeeded
    stored = stored_events(db, "AAPL")
    assert any(r.event_date == future for r in stored)      # store grew


# ------------------------------------------- T083c: base rates in the brief

def test_base_rates_summary_computes_and_degrades(db):  # noqa: F811
    """4 stored past reactions -> compact summary (median, closed-down frac);
    thin store -> available False with the EDGAR pointer."""
    from api.brief import _base_rates_summary

    today = date.today()
    past = [today - timedelta(days=40 * (i + 1)) for i in range(4)]
    record_events(db, [ev("AAPL", d, hint="bmo", actual=2.0, est=1.0)
                       for d in past])
    with bars_market() as m:
        out = _base_rates_summary(db, m, "AAPL")
    assert out["available"] is True
    assert out["events_measured"] == 4
    assert isinstance(out["median_event_day_move"], float)
    assert 0.0 <= out["closed_down_frac"] <= 1.0
    assert "not a prediction" in out["note"]

    with bars_market() as m:
        thin = _base_rates_summary(db, m, "MSFT")     # nothing stored
    assert thin["available"] is False
    assert "EDGAR backfills" in thin["why"]


def test_base_rates_summary_never_raises(db):  # noqa: F811
    """A broken market client degrades to a why — the brief must survive."""
    from api.brief import _base_rates_summary

    class Boom:
        def get_daily_bars(self, *a, **k):
            raise RuntimeError("feed down")

    today = date.today()
    record_events(db, [ev("AAPL", today - timedelta(days=40 * (i + 1)),
                          hint="bmo") for i in range(4)])
    out = _base_rates_summary(db, Boom(), "AAPL")
    assert out["available"] is False and "RuntimeError" in out["why"]
