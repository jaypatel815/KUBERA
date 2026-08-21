"""T121 — FinnhubClient + surprises enrichment. Fixtures mirror the owner's
probe (2026-08-20: 4 quarters actual-vs-estimate; 403 = paywalled)."""

from datetime import date
from types import SimpleNamespace

import httpx
import pytest
from test_paper_loop import db  # noqa: F401

from api.mcp_server import close_tool_context
from api.tools import ToolContext
from data.earnings_store import enrich_from_surprises, record_events, stored_events
from data.finnhub import EarningsSurprise, FinnhubClient, FinnhubError
from settings import ConfigError, KuberaSettings

SURPRISES = [  # probe-faithful: list of dicts with actual/estimate/period
    {"actual": 1.57, "estimate": 1.43, "period": "2026-06-30",
     "symbol": "AAPL", "surprise": 0.14},
    {"actual": 2.40, "estimate": 2.35, "period": "2026-03-31", "symbol": "AAPL"},
    {"actual": None, "estimate": 1.10, "period": "2025-12-31", "symbol": "AAPL"},
    {"actual": 1.0, "estimate": 1.0, "period": "not-a-date"},   # unparsed
]

NEWS = [
    {"headline": "Apple ships thing", "datetime": 1755600000,
     "source": "wire", "url": "https://x/1"},
    {"headline": "Older item", "datetime": 1755000000,
     "source": "wire", "url": "https://x/2"},
    {"no_headline": True},                                       # dropped
]


def _client(payload, status=200) -> FinnhubClient:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "token=" in str(request.url)          # key rides as param
        return httpx.Response(status, json=payload)

    return FinnhubClient(
        settings=KuberaSettings(_env_file=None, finnhub_api_key="k"),
        transport=httpx.MockTransport(handler))


def test_missing_key_is_actionable():
    with pytest.raises(ConfigError, match="FINNHUB_API_KEY"):
        FinnhubClient(settings=KuberaSettings(_env_file=None, finnhub_api_key=None))


def test_surprises_parse_fail_closed_and_sorted():
    with _client(SURPRISES) as c:
        r = c.earnings_surprises("aapl")
    assert r.symbol == "AAPL" and r.unparsed == 1
    assert [s.period_end.isoformat() for s in r.rows] == \
        ["2025-12-31", "2026-03-31", "2026-06-30"]   # oldest first
    assert r.rows[-1].eps_actual == 1.57 and r.rows[-1].eps_estimated == 1.43
    assert r.rows[0].eps_actual is None              # kept, not guessed


def test_named_refusals():
    with _client({}, status=403) as c:
        with pytest.raises(FinnhubError, match="PAYWALLED"):
            c.earnings_surprises("AAPL")
    with _client({}, status=401) as c:
        with pytest.raises(FinnhubError, match="FINNHUB_API_KEY"):
            c.earnings_surprises("AAPL")
    with _client({}, status=429) as c:
        with pytest.raises(FinnhubError, match="do not retry"):
            c.earnings_surprises("AAPL")
    with _client({"not": "a list"}) as c:
        with pytest.raises(FinnhubError, match="shape changed"):
            c.earnings_surprises("AAPL")


def test_news_newest_first_capped_and_counted():
    with _client(NEWS) as c:
        r = c.company_news("AAPL", days=31)
    assert r.total_returned == 2                     # headline-less dropped
    assert r.items[0].headline == "Apple ships thing"
    assert r.items[0].published_utc is not None


# ------------------------------------------------------- enrichment rules


def _seed(db_, symbol, dates):  # noqa: ANN001
    record_events(db_, [SimpleNamespace(symbol=symbol, date=date.fromisoformat(d),
                                        time_hint=None, eps_estimated=None,
                                        eps_actual=None) for d in dates],
                  source="test")


def test_unambiguous_match_enriches_empty_fields_only(db):  # noqa: F811
    # period 2026-06-30 -> exactly one report (2026-07-30) inside 120d: enrich
    _seed(db, "AAPL", ["2026-07-30", "2026-04-30"])
    out = enrich_from_surprises(db, "AAPL", [
        EarningsSurprise("AAPL", date(2026, 6, 30), 1.57, 1.43),
        EarningsSurprise("AAPL", date(2026, 3, 31), 2.40, 2.35),
    ])
    assert out == {"enriched": 2, "ambiguous": 0, "unmatched": 0, "already": 0}
    rows = {r.event_date: r for r in stored_events(db, "AAPL")}
    assert rows["2026-07-30"].eps_actual == 1.57
    assert rows["2026-04-30"].eps_estimated == 2.35


def test_ambiguity_and_no_match_are_counted_never_guessed(db):  # noqa: F811
    # TWO stored events inside the window -> ambiguous, skipped
    _seed(db, "AAPL", ["2026-07-15", "2026-08-15"])
    out = enrich_from_surprises(db, "AAPL", [
        EarningsSurprise("AAPL", date(2026, 6, 30), 1.57, 1.43),   # 2 cands
        EarningsSurprise("AAPL", date(2020, 6, 30), 1.0, 1.0),     # 0 cands
    ])
    assert out == {"enriched": 0, "ambiguous": 1, "unmatched": 1, "already": 0}
    assert all(r.eps_actual is None for r in stored_events(db, "AAPL"))


def test_existing_values_never_overwritten(db):  # noqa: F811
    _seed(db, "AAPL", ["2026-07-30"])
    row = stored_events(db, "AAPL")[0]
    row.eps_actual = 9.99                            # pre-existing truth
    db.commit()
    out = enrich_from_surprises(db, "AAPL", [
        EarningsSurprise("AAPL", date(2026, 6, 30), 1.57, None)])
    assert out["already"] == 1 and out["enriched"] == 0
    assert stored_events(db, "AAPL")[0].eps_actual == 9.99


# ------------------------------------------------------------ lifecycle


def test_close_list_includes_finnhub_t106_class():
    closed = []
    fake = SimpleNamespace(close=lambda: closed.append("finnhub"))
    close_tool_context(ToolContext(finnhub=fake))
    assert closed == ["finnhub"]                     # a member missing = leak
