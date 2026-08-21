"""T023 v1 — FMP earnings calendar (D030). All MockTransport; no network.

The fixture rows are built from FMP's documented earning_calendar shape. That
means these tests prove the parser does what we BELIEVE the API returns — the
same honesty note as the Schwab tests. The owner-side proof is the probe
(scripts/fmp_check.py: calendar OK, 77 rows) plus the first live morning brief.
"""

from datetime import date, datetime

import httpx
import pytest

from api.brief import _earnings_section
from api.tools import ToolContext, ToolError, registry
from data.fmp import FmpClient, FmpError
from settings import ConfigError, KuberaSettings

CAL_JSON = [
    {"symbol": "NVDA", "date": "2026-08-26", "epsEstimated": 1.01,
     "revenueEstimated": 4.61e10, "time": "amc", "fiscalDateEnding": "2026-07-31"},
    {"symbol": "AAPL", "date": "2026-08-28", "epsEstimated": None, "time": "bmo"},
    {"symbol": "", "date": "2026-08-29"},                    # unparseable: no symbol
    {"symbol": "XYZ", "date": "not-a-date"},                 # unparseable: bad date
]


def fmp_settings(**over) -> KuberaSettings:
    base = dict(_env_file=None, fmp_api_key="test-key")
    base.update(over)
    return KuberaSettings(**base)


def client_with(json_body, status=200) -> FmpClient:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "apikey=test-key" in str(request.url)
        return httpx.Response(status, json=json_body)

    return FmpClient(settings=fmp_settings(), transport=httpx.MockTransport(handler))


def test_missing_key_is_actionable():
    with pytest.raises(ConfigError, match="FMP_API_KEY"):
        FmpClient(settings=KuberaSettings(_env_file=None, fmp_api_key=None))


def test_calendar_parses_and_reports_unparsed():
    with client_with(CAL_JSON) as c:
        cal = c.earnings_calendar(date(2026, 8, 20), date(2026, 9, 3))
    assert [e.symbol for e in cal.events] == ["NVDA", "AAPL"]   # sorted by date
    nvda = cal.events[0]
    assert nvda.date == date(2026, 8, 26)
    assert nvda.time_hint == "amc"
    assert nvda.eps_estimated == pytest.approx(1.01)
    assert len(cal.unparsed) == 2                               # reported, not dropped
    assert any("refusing to guess" in u["why"] for u in cal.unparsed)


def test_rate_limit_and_paywall_are_named():
    with client_with({"error": "limit"}, status=429) as c:
        with pytest.raises(FmpError, match="250 requests/day"):
            c.earnings_calendar(date(2026, 8, 20), date(2026, 8, 21))
    with client_with({"error": "premium"}, status=403) as c:
        with pytest.raises(FmpError, match="paywalled"):
            c.earnings_calendar(date(2026, 8, 20), date(2026, 8, 21))


def test_non_list_response_refuses():
    with client_with({"unexpected": "object"}) as c:
        with pytest.raises(FmpError, match="refusing to guess"):
            c.earnings_calendar(date(2026, 8, 20), date(2026, 8, 21))


def test_backwards_window_rejected():
    with client_with([]) as c:
        with pytest.raises(ValueError, match="to_date"):
            c.earnings_calendar(date(2026, 8, 21), date(2026, 8, 20))


# ---------------------------------------------------------------- tool + brief

def test_tool_filters_symbols_and_separates_estimates():
    with client_with(CAL_JSON) as c:
        out = registry.execute("get_earnings_calendar",
                               {"days": 14, "symbols": "nvda"},
                               ToolContext(fmp=c))
    assert out["count"] == 1
    assert out["events"][0]["symbol"] == "NVDA"
    assert out["unparsed_rows"] == 2
    assert "third-party" in out["note"]      # estimates attributed, not owned


def test_tool_without_fmp_context_is_a_clear_error():
    with pytest.raises(ToolError, match="fmp"):
        registry.execute("get_earnings_calendar", {}, ToolContext())


def test_brief_section_filters_to_held_and_degrades():
    with client_with(CAL_JSON) as c:
        sec = _earnings_section(c, {"NVDA"})
    assert [e["symbol"] for e in sec["upcoming"]] == ["NVDA"]
    assert "unparseable" in (sec["note"] or "")

    # no client -> note, never an error
    off = _earnings_section(None, {"NVDA"})
    assert off["upcoming"] == [] and "FMP_API_KEY" in off["note"]

    # a failing client -> note, never an error
    with client_with({"error": "x"}, status=500) as bad:
        broken = _earnings_section(bad, {"NVDA"})
    assert broken["upcoming"] == [] and "unavailable" in broken["note"]


def test_asof_rides_along():
    with client_with([]) as c:
        cal = c.earnings_calendar(date(2026, 8, 20), date(2026, 8, 21))
    assert cal.asof and datetime.fromisoformat(cal.asof)
    assert cal.source == "fmp-free"


# ---------------------------------------------------------------- T023b

def routed_client(routes: dict) -> FmpClient:
    """MockTransport routing by path suffix: {'/stable/profile': (status, json)}."""
    def handler(request: httpx.Request) -> httpx.Response:
        for suffix, (status, body) in routes.items():
            if request.url.path.endswith(suffix):
                return httpx.Response(status, json=body)
        return httpx.Response(404, json={})

    return FmpClient(settings=fmp_settings(), transport=httpx.MockTransport(handler))


def test_t023b_statement_fetchers_and_market_cap():
    routes = {
        "/stable/cash-flow-statement": (200, [{"date": "2025-12-31",
                                               "freeCashFlow": 80000.0}]),
        "/stable/balance-sheet-statement": (200, [{"date": "2025-12-31",
                                                   "totalDebt": 50000.0,
                                                   "totalStockholdersEquity": 200000.0,
                                                   "totalAssets": 400000.0}]),
        "/stable/profile": (200, [{"symbol": "AAPL", "marketCap": 1600000.0}]),
    }
    with routed_client(routes) as c:
        assert c.cash_flow_statement("aapl")[0]["freeCashFlow"] == 80000.0
        assert c.balance_sheet("aapl")[0]["totalDebt"] == 50000.0
        assert c.profile_market_cap("aapl") == 1600000.0


def test_t023b_paywalled_balance_sheet_is_named_and_shape_checked():
    with routed_client({"/stable/balance-sheet-statement": (403, {})}) as c:
        with pytest.raises(FmpError, match="paywalled"):
            c.balance_sheet("AAPL")
    with routed_client({"/stable/profile": (200, {"not": "a list"})}) as c:
        with pytest.raises(FmpError, match="non-list"):
            c.profile_market_cap("AAPL")


def test_t023b_profile_without_usable_cap_returns_none():
    with routed_client({"/stable/profile": (200, [{"symbol": "AAPL"}])}) as c:
        assert c.profile_market_cap("AAPL") is None
