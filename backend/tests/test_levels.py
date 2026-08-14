"""Support/resistance (T051) — clustering hand-walked swing by swing, plus the
mixed-kind (support-becomes-resistance) case and the registry tool/endpoint."""

import httpx
import pytest
from fastapi.testclient import TestClient
from test_alpaca import paper_settings

from analysis.levels import find_levels
from api.main import app
from api.tools import ToolContext, ToolError, registry
from data.market_data import MarketDataClient

client = TestClient(app)


def _dates(n: int) -> list[str]:
    return [f"d{i:03d}" for i in range(n)]


# --- fixture 1: three-touch support & resistance + a one-touch stray ----------
# swing highs: 12.0@d1, 12.1@d4, 12.05@d7 (cluster) and 14.0@d9 (stray, dropped)
# swing lows:  9.0@d1, 9.05@d3, 8.95@d5 (cluster); monotone tail adds none
HIGHS_1 = [10.0, 12.0, 10.0, 10.5, 12.1, 10.0, 10.5, 12.05, 10.0, 14.0, 10.0, 10.0, 10.2]
LOWS_1 = [9.5, 9.0, 9.6, 9.05, 9.7, 8.95, 9.40, 9.41, 9.42, 9.43, 9.44, 9.45, 9.46]
CLOSES_1 = [9.8, 11.0, 9.8, 10.0, 11.5, 9.5, 10.0, 11.5, 9.8, 13.5, 9.9, 9.8, 10.1]

MICRO = dict(swing_span=1, lookback=120)


def test_levels_hand_walked():
    r = find_levels(HIGHS_1, LOWS_1, CLOSES_1, _dates(13), **MICRO)
    assert r.swings_found == 7
    assert len(r.levels) == 2  # the 14.0 stray has one touch -> noise, dropped

    support, resistance = r.levels
    # mean(8.95, 9.0, 9.05) = 9.0 — three rejections define the floor
    assert support.price == pytest.approx(9.0)
    assert support.touches == 3 and support.kind == "support"
    assert (support.first_date, support.last_date) == ("d001", "d005")
    # mean(12.0, 12.05, 12.1) = 12.05
    assert resistance.price == pytest.approx(12.05)
    assert resistance.touches == 3 and resistance.kind == "resistance"

    assert r.last_close == pytest.approx(10.1)
    assert r.nearest_support is support and r.nearest_resistance is resistance
    assert support.distance_frac == pytest.approx(9.0 / 10.1 - 1)
    assert resistance.distance_frac == pytest.approx(12.05 / 10.1 - 1)


def test_min_touches_one_keeps_the_stray():
    r = find_levels(HIGHS_1, LOWS_1, CLOSES_1, _dates(13), min_touches=1, **MICRO)
    assert len(r.levels) == 3
    assert r.levels[-1].price == pytest.approx(14.0)
    assert r.levels[-1].touches == 1


def test_wide_tolerance_merges_the_stray():
    # tol 20%: 14.0 <= mean(12.0,12.05,12.1)*1.2 = 14.46 -> one 4-touch cluster
    r = find_levels(HIGHS_1, LOWS_1, CLOSES_1, _dates(13),
                    swing_span=1, tolerance_frac=0.2)
    resistance = r.levels[-1]
    assert resistance.touches == 4
    assert resistance.price == pytest.approx((12.0 + 12.05 + 12.1 + 14.0) / 4)


# --- fixture 2: old support becomes resistance (mixed kind) -------------------
# swing low 10.0@d1 while price lived above; after the breakdown, the rally back
# rejects at swing high 10.05@d6 -> one 2-touch MIXED level at 10.025.
HIGHS_2 = [11.0, 11.1, 11.2, 11.3, 11.4, 9.8, 10.05, 9.7, 9.75, 9.8]
LOWS_2 = [10.5, 10.0, 10.6, 10.7, 10.8, 9.6, 9.5, 9.4, 9.55, 9.7]
CLOSES_2 = [10.8, 10.5, 11.0, 11.1, 11.0, 9.7, 9.9, 9.5, 9.7, 9.75]


def test_mixed_kind_level_and_no_support_below():
    r = find_levels(HIGHS_2, LOWS_2, CLOSES_2, _dates(10), **MICRO)
    assert len(r.levels) == 1  # 9.4 and 11.4 are one-touch strays
    level = r.levels[0]
    assert level.kind == "mixed"
    assert level.price == pytest.approx(10.025)
    assert level.touches == 2
    assert (level.first_date, level.last_date) == ("d001", "d006")
    # last close 9.75 sits UNDER the old floor: it is now the nearest resistance
    assert r.nearest_resistance is level
    assert r.nearest_support is None
    assert level.distance_frac == pytest.approx(10.025 / 9.75 - 1)


# --- validation ---------------------------------------------------------------

@pytest.mark.parametrize(
    "kwargs, match",
    [
        (dict(tolerance_frac=0.0), "tolerance_frac"),
        (dict(tolerance_frac=0.3), "tolerance_frac"),
        (dict(swing_span=0), ">= 1"),
        (dict(min_touches=0), ">= 1"),
        (dict(lookback=2), "lookback"),
    ],
)
def test_bad_params(kwargs, match):
    with pytest.raises(ValueError, match=match):
        find_levels(HIGHS_2, LOWS_2, CLOSES_2, _dates(10), **kwargs)


def test_bad_bars():
    with pytest.raises(ValueError, match="equal length"):
        find_levels(HIGHS_2[:9], LOWS_2, CLOSES_2, _dates(10))
    with pytest.raises(ValueError, match="low"):
        find_levels(LOWS_2, HIGHS_2, CLOSES_2, _dates(10))  # swapped -> low > high
    with pytest.raises(ValueError, match="at least"):
        find_levels([10.0, 10.0], [9.0, 9.0], [9.5, 9.5], _dates(2), swing_span=2)


# --- registry tool + endpoint (default span=2 on a clean 60-bar triangle) -----
# pattern peaks at exactly 105 / troughs at 95: resistance 105.5 (7 touches),
# support 94.5 (7 touches — the i=1 trough is inside the span-2 edge, excluded).
PATTERN = [97.5, 95.0, 97.5, 100.0, 102.5, 105.0, 102.5, 100.0]
TRIANGLE_BARS = {
    "symbol": "SPY",
    "next_page_token": None,
    "bars": [
        {"t": f"2026-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}T04:00:00Z",
         "o": c, "h": c + 0.5, "l": c - 0.5, "c": c, "v": 1}
        for i in range(60)
        for c in [PATTERN[i % 8]]
    ],
}


def market_fake(bars_json: dict) -> MarketDataClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=bars_json)

    return MarketDataClient(settings=paper_settings(), transport=httpx.MockTransport(handler))


def test_get_levels_tool_executes():
    with market_fake(TRIANGLE_BARS) as m:
        out = registry.execute("get_levels", {"symbol": "SPY"}, ToolContext(market=m))
    r = out["levels"]
    assert [round(level["price"], 1) for level in r["levels"]] == [94.5, 105.5]
    assert [level["touches"] for level in r["levels"]] == [7, 7]
    assert r["nearest_support"]["price"] == pytest.approx(94.5)
    assert r["nearest_resistance"]["price"] == pytest.approx(105.5)
    assert r["last_close"] == pytest.approx(100.0)
    assert out["source"] == "alpaca-data-iex" and out["asof"]


def test_get_levels_tool_rejects_thin_history():
    thin = {"symbol": "SPY", "next_page_token": None,
            "bars": TRIANGLE_BARS["bars"][:5]}
    with market_fake(thin) as m, pytest.raises(ToolError, match="20"):
        registry.execute("get_levels", {"symbol": "SPY"}, ToolContext(market=m))


def test_levels_endpoint():
    from api import main as main_module

    def fake_client_dep():
        with market_fake(TRIANGLE_BARS) as m:
            yield m

    app.dependency_overrides[main_module.get_market_client] = fake_client_dep
    try:
        r = client.get("/api/levels/SPY")
    finally:
        app.dependency_overrides.pop(main_module.get_market_client)
    assert r.status_code == 200
    body = r.json()
    assert body["levels"]["nearest_resistance"]["touches"] == 7
    assert body["levels"]["as_of_date"] == "2026-03-04"  # i=59 -> month 3, day 4
    assert body["asof"]
