"""Regime classifier (T050): hand-computed micros + synthetic regime fixtures built
straight from the owner's doctrine (docs/research/regime-trading-notes.md) — sawtooth
trends with swing structure, a stationary range, a coil, and the low-volume ->
consolidation -> volume-expansion -> breakout pattern (plus its fakeout twin)."""

import httpx
import pytest
from fastapi.testclient import TestClient
from test_alpaca import paper_settings

from analysis.regime import classify_regime
from api.main import app
from api.tools import ToolContext, ToolError, registry
from data.market_data import MarketDataClient

client = TestClient(app)


# --- fixture builders (deterministic) ----------------------------------------

def _dates(n: int) -> list[str]:
    return [f"d{i:03d}" for i in range(n)]


def _from_closes(closes, hi=0.5, lo=0.5, vol=1_000_000.0):
    """Symmetric additive high/low margins and flat volume."""
    return (
        [c + hi for c in closes],
        [c - lo for c in closes],
        list(closes),
        [vol] * len(closes),
        _dates(len(closes)),
    )


def _sawtooth(factors: list[float], n: int, start: float = 100.0) -> list[float]:
    closes = [start]
    for i in range(n - 1):
        closes.append(closes[-1] * factors[i % len(factors)])
    return closes


# 20 cycles of 4 rises then a dip: higher swing highs AND higher swing lows (+5%/cycle)
TREND_UP = _sawtooth([1.02, 1.02, 1.02, 1.02, 0.97], 100)
# the mirror: 4 drops then a bounce (-5%/cycle)
TREND_DOWN = _sawtooth([0.98, 0.98, 0.98, 0.98, 1.03], 100)
# stationary 95..105 triangle, period 8, ending mid-range; equal swing highs/lows
RANGE_PATTERN = [97.5, 95.0, 97.5, 100.0, 102.5, 105.0, 102.5, 100.0]
RANGE = RANGE_PATTERN * 12  # 96 bars
# 64 wide bars then 32 quiet bars around 100 on HALF the volume — the coil
QUIET_PATTERN = [99.5, 100.0, 100.5, 100.0]
COIL_CLOSES = RANGE_PATTERN * 8 + QUIET_PATTERN * 8  # 96 bars


def _coil_bars():
    highs, lows, closes, _, dates = _from_closes(COIL_CLOSES)
    volumes = [1_000_000.0] * 64 + [500_000.0] * 32
    return highs, lows, closes, volumes, dates


def _breakout_bars(final_volume: float):
    """The coil plus one escape bar: close 103 above the quiet range's 101 high."""
    highs, lows, closes, volumes, dates = _coil_bars()
    return (
        highs + [103.2],
        lows + [100.0],
        closes + [103.0],
        volumes + [final_volume],
        dates + ["d096"],
    )


# --- the four regimes on doctrine fixtures -----------------------------------

def test_sawtooth_uptrend_is_trending_up():
    r = classify_regime(*_from_closes(TREND_UP), volume_feed="test-fixture")
    assert r.regime == "trending_up"
    assert r.structure == "up" and r.structure_method == "swings"
    # higher swing highs AND higher swing lows, per the doctrine
    assert r.swing_highs[1].price > r.swing_highs[0].price
    assert r.swing_lows[1].price > r.swing_lows[0].price
    # each new bar makes a new high — yet a matured trend outranks its own escape
    assert r.escaped_up is True
    # swings + flat-volume participation always pass; range expansion is phase-luck
    assert 0.65 <= r.confidence <= 0.8
    assert "higher highs" in r.reason


def test_sawtooth_downtrend_is_trending_down():
    r = classify_regime(*_from_closes(TREND_DOWN), volume_feed="test-fixture")
    assert r.regime == "trending_down"
    assert r.structure == "down" and r.structure_method == "swings"
    assert r.swing_highs[1].price < r.swing_highs[0].price
    assert r.escaped_down is True
    assert "lower highs" in r.reason


def test_stationary_triangle_is_range_bound():
    r = classify_regime(*_from_closes(RANGE), volume_feed="test-fixture")
    assert r.regime == "range_bound"
    # equal 105s / equal 95s: swings exist but neither rise nor fall
    assert r.structure == "none" and r.structure_method == "swings"
    assert r.range_high == pytest.approx(105.5) and r.range_low == pytest.approx(94.5)
    # every 20-bar window spans the identical full range -> percentile 1.0, no coil
    assert r.range_width_percentile == pytest.approx(1.0)
    assert r.close_position_in_range == pytest.approx(0.5)
    # structure_none + mid_range_close + quiet volume (rvol 1.0) all pass
    assert r.rvol == pytest.approx(1.0)
    assert r.confidence == pytest.approx(0.8)


def test_quiet_narrow_range_is_a_coil():
    r = classify_regime(*_coil_bars(), volume_feed="test-fixture")
    assert r.regime == "breakout_watch"
    assert not (r.escaped_up or r.escaped_down)
    # current width 2/100; only the 12 all-quiet windows + the one seam window
    # (its lone wide-era bar closes inside the quiet band) are as narrow: 13 of 76
    assert r.range_width_percentile == pytest.approx(13 / 76)
    assert r.checks == {
        "escaped": False, "volume_confirmed": False, "tight_range": True,
    }
    assert r.confidence == pytest.approx(0.5)
    assert "coiled" in r.reason


def test_volume_confirmed_breakout_from_the_coil():
    r = classify_regime(*_breakout_bars(1_500_000.0), volume_feed="test-fixture")
    assert r.regime == "breakout_watch"
    assert r.escaped_up is True and r.suspected_fakeout is False
    assert r.rvol == pytest.approx(3.0)  # 1.5M vs the 500k quiet baseline
    # quiet-window count grows by one; two seam windows also sit at/below the
    # widened current window (hand-walked): 15 of 77
    assert r.range_width_percentile == pytest.approx(15 / 77)
    assert r.checks == {
        "escaped": True, "volume_confirmed": True, "tight_range": True,
    }
    assert r.confidence == pytest.approx(0.8)
    assert "with volume confirmation" in r.reason


def test_weak_volume_escape_is_a_suspected_fakeout():
    r = classify_regime(*_breakout_bars(250_000.0), volume_feed="test-fixture")
    assert r.regime == "breakout_watch"
    assert r.rvol == pytest.approx(0.5)
    assert r.suspected_fakeout is True
    assert r.checks["volume_confirmed"] is False
    assert r.confidence == pytest.approx(0.65)  # escaped + tight, no volume
    assert "WITHOUT volume confirmation" in r.reason


# --- hand-computed micros (small lookbacks) ----------------------------------

MICRO = dict(range_lookback=3, rvol_baseline=3, swing_span=1)


def test_rvol_arithmetic_and_thin_history_degradation():
    flat = [100.0] * 4
    r = classify_regime(
        flat, flat, flat, [10.0, 20.0, 30.0, 40.0], _dates(4),
        volume_feed="test-fixture", **MICRO,
    )
    assert r.rvol == pytest.approx(2.0)  # 40 / mean(10, 20, 30)
    assert r.range_width_percentile is None  # 1 other window < 10 -> no percentile
    assert r.close_position_in_range is None  # zero-width range
    assert r.structure_method == "insufficient"
    assert r.regime == "range_bound"
    # checks: structure_none only (pos None, rvol 2.0 not quiet)
    assert r.confidence == pytest.approx(0.5)


def test_escape_detection_hand():
    closes = [100.0, 100.0, 100.0, 100.0, 105.0]
    r = classify_regime(
        closes, closes, closes, [10.0, 10.0, 10.0, 10.0, 30.0], _dates(5),
        volume_feed="test-fixture", **MICRO,
    )
    assert r.escaped_up is True and r.escaped_down is False
    assert r.regime == "breakout_watch"
    assert r.rvol == pytest.approx(3.0) and r.suspected_fakeout is False
    assert r.confidence == pytest.approx(0.65)  # escaped + confirmed, no percentile
    assert "escaped above" in r.reason


def test_escape_on_weak_volume_flags_fakeout_hand():
    closes = [100.0, 100.0, 100.0, 100.0, 105.0]
    r = classify_regime(
        closes, closes, closes, [30.0, 30.0, 30.0, 30.0, 15.0], _dates(5),
        volume_feed="test-fixture", **MICRO,
    )
    assert r.rvol == pytest.approx(0.5)
    assert r.suspected_fakeout is True
    assert r.confidence == pytest.approx(0.5)  # escaped only


def test_swing_detection_hand():
    highs = [10.0, 12.0, 10.0, 11.0, 14.0, 11.0, 12.0]
    lows = [9.0, 10.0, 8.0, 9.0, 10.0, 9.0, 11.0]
    closes = [9.5, 11.0, 9.0, 10.0, 12.0, 10.0, 11.5]
    r = classify_regime(
        highs, lows, closes, [10.0] * 7, _dates(7),
        volume_feed="test-fixture", **MICRO,
    )
    assert [(p.date, p.price) for p in r.swing_highs] == [("d001", 12.0), ("d004", 14.0)]
    assert [(p.date, p.price) for p in r.swing_lows] == [("d002", 8.0), ("d005", 9.0)]
    assert r.structure == "up" and r.structure_method == "swings"
    assert r.regime == "trending_up"


def test_monotone_series_uses_sma_slope_fallback():
    closes = [100.0 * 1.01**i for i in range(30)]
    r = classify_regime(
        closes, closes, closes, [10.0] * 30, _dates(30),
        volume_feed="test-fixture",
        range_lookback=5, rvol_baseline=5, swing_span=2,
    )
    assert r.swing_highs == [] and r.swing_lows == []  # monotone has no swings
    assert r.structure == "up" and r.structure_method == "sma_slope"
    assert r.regime == "trending_up"


# --- D006 feed labeling -------------------------------------------------------

def test_volume_feed_is_labeled_and_required():
    flat = [100.0] * 4
    r = classify_regime(
        flat, flat, flat, [10.0] * 4, _dates(4), volume_feed="alpaca-data-iex", **MICRO
    )
    assert r.volume_feed == "alpaca-data-iex"
    assert "SIP" in r.volume_note and "alpaca-data-iex" in r.volume_note
    with pytest.raises(ValueError, match="volume_feed"):
        classify_regime(
            flat, flat, flat, [10.0] * 4, _dates(4), volume_feed="  ", **MICRO
        )


# --- validation (bad input never classifies) ----------------------------------

@pytest.mark.parametrize(
    "mutate, match",
    [
        (lambda b: b["highs"].pop(), "equal length"),
        (lambda b: b.update(closes=b["closes"][:3], highs=b["highs"][:3],
                            lows=b["lows"][:3], volumes=b["volumes"][:3],
                            dates=b["dates"][:3]), "at least 4 bars"),
        (lambda b: b["lows"].__setitem__(1, 200.0), "low"),
        (lambda b: b["closes"].__setitem__(1, 999.0), "outside"),
        (lambda b: b["volumes"].__setitem__(1, -5.0), "volume"),
        (lambda b: b["closes"].__setitem__(1, -1.0), "> 0"),
    ],
)
def test_bad_input_raises(mutate, match):
    bars = {
        "highs": [101.0] * 4, "lows": [99.0] * 4, "closes": [100.0] * 4,
        "volumes": [10.0] * 4, "dates": _dates(4),
    }
    mutate(bars)
    with pytest.raises(ValueError, match=match):
        classify_regime(
            bars["highs"], bars["lows"], bars["closes"], bars["volumes"],
            bars["dates"], volume_feed="test-fixture", **MICRO,
        )


# --- registry tool + endpoint -------------------------------------------------

BREAKOUT_BARS_JSON = {
    "symbol": "SPY",
    "next_page_token": None,
    "bars": [
        {"t": f"2026-07-{d:02d}T04:00:00Z", "o": 100, "h": 100.5, "l": 99.5,
         "c": 100.0, "v": 1_000_000}
        for d in range(1, 21)
    ] + [
        {"t": "2026-07-21T04:00:00Z", "o": 101, "h": 105.5, "l": 100.5,
         "c": 105.0, "v": 3_000_000},
    ],
}


def market_fake(bars_json: dict) -> MarketDataClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=bars_json)

    return MarketDataClient(settings=paper_settings(), transport=httpx.MockTransport(handler))


def test_get_regime_tool_executes():
    with market_fake(BREAKOUT_BARS_JSON) as m:
        out = registry.execute("get_regime", {"symbol": "SPY"}, ToolContext(market=m))
    reading = out["regime"]
    assert reading["regime"] == "breakout_watch"
    assert reading["escaped_up"] is True and reading["rvol"] == pytest.approx(3.0)
    assert reading["volume_feed"] == "alpaca-data-iex"  # D006 label flows from the client
    assert reading["as_of_date"] == "2026-07-21"
    assert out["asof"] and out["source"] == "alpaca-data-iex"


def test_get_regime_tool_rejects_thin_history():
    thin = {"symbol": "SPY", "next_page_token": None,
            "bars": BREAKOUT_BARS_JSON["bars"][:5]}
    with market_fake(thin) as m, pytest.raises(ToolError, match="21"):
        registry.execute("get_regime", {"symbol": "SPY"}, ToolContext(market=m))


def test_regime_endpoint(monkeypatch):
    from api import main as main_module

    def fake_client_dep():
        with market_fake(BREAKOUT_BARS_JSON) as m:
            yield m

    app.dependency_overrides[main_module.get_market_client] = fake_client_dep
    try:
        r = client.get("/api/regime/SPY")
    finally:
        app.dependency_overrides.pop(main_module.get_market_client)
    assert r.status_code == 200
    body = r.json()
    assert body["regime"]["regime"] == "breakout_watch"
    assert body["regime"]["volume_note"].startswith("RVOL is relative")
    assert body["asof"]
