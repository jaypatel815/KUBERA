"""Expected-move engine (T077) — percentile bands hand-computed via inclusive
interpolation, payoff arithmetic, vol-clustering conditioning, and the honesty
constraints (never a forecast; overlap caveat in every reading)."""

import httpx
import pytest
from fastapi.testclient import TestClient
from test_alpaca import paper_settings

from analysis.expected_move import expected_move
from api.main import app
from api.tools import ToolContext, ToolError, registry
from data.market_data import MarketDataClient

client = TestClient(app)


def _dates(n):
    return [f"d{i:03d}" for i in range(n)]


def test_percentile_bands_hand():
    # 1-day samples: [+10%, -10%, +10%]; inclusive interpolation on 3 points:
    # h = 2*p -> p05: -0.1 + 0.1*0.2 = -0.08; p25: 0.0; p50/p75/p95: 0.1
    closes = [100.0, 110.0, 99.0, 108.9]
    r = expected_move(closes, _dates(4), horizon_days=1, min_samples=2)
    u = r.unconditional
    assert u.samples == 3
    assert u.percentiles["p05"] == pytest.approx(-0.08)
    assert u.percentiles["p25"] == pytest.approx(0.0)
    assert u.percentiles["p50"] == pytest.approx(0.1)
    assert u.percentiles["p95"] == pytest.approx(0.1)
    assert u.band_prices["p50"] == pytest.approx(108.9 * 1.1)
    assert u.up_frac == pytest.approx(2 / 3)
    assert u.payoff_ratio == pytest.approx(1.0)
    # too little history for a 20-bar vol window -> conditioning degrades to None
    assert r.current_vol_tercile is None and r.conditioned is None
    assert "NOT a forecast" in r.note


def test_payoff_ratio_and_typical_move_hand():
    # samples [+20%, -10%, +10%, -5%]: winners avg 15%, losers avg 7.5% -> 2.0
    closes = [100.0, 120.0, 108.0, 118.8, 112.86]
    r = expected_move(closes, _dates(5), horizon_days=1, min_samples=2)
    u = r.unconditional
    assert u.up_frac == pytest.approx(0.5)
    assert u.payoff_ratio == pytest.approx(2.0)
    assert u.expected_abs_move_frac == pytest.approx(0.1)  # median of |.2 .1 .1 .05|


def test_all_up_history_has_no_payoff_ratio():
    closes = [100.0 * 1.01**i for i in range(10)]
    r = expected_move(closes, _dates(10), horizon_days=1, min_samples=2)
    assert r.unconditional.up_frac == pytest.approx(1.0)
    assert r.unconditional.payoff_ratio is None  # no losers to divide by


def test_vol_clustering_narrows_bands_on_a_quiet_tape():
    # 100 wild bars (±3%) then 100 quiet bars (±0.1%): "now" is a low-vol regime,
    # so conditioned bands must be far narrower than the wild-contaminated
    # unconditional ones — quiet tape -> narrower HONEST expectations.
    closes = [100.0]
    for i in range(99):
        closes.append(closes[-1] * (1.03 if i % 2 == 0 else 1 / 1.03))
    for i in range(100):
        closes.append(closes[-1] * (1.001 if i % 2 == 0 else 1 / 1.001))
    r = expected_move(closes, _dates(200), horizon_days=1)
    assert r.current_vol_tercile == "low"
    assert r.conditioned is not None and r.conditioned.samples >= 20
    assert r.conditioned.percentiles["p95"] < r.unconditional.percentiles["p95"] / 5
    assert r.conditioned.percentiles["p05"] > r.unconditional.percentiles["p05"] / 5


@pytest.mark.parametrize(
    "kwargs, match",
    [
        (dict(horizon_days=0), ">= 1"),
        (dict(vol_window=1), ">= 1|>= 2"),
        (dict(min_samples=1), ">= 2"),
    ],
)
def test_param_validation(kwargs, match):
    closes = [100.0] * 50
    with pytest.raises(ValueError, match=match):
        expected_move(closes, _dates(50), **kwargs)


def test_input_validation():
    with pytest.raises(ValueError, match="equal length"):
        expected_move([100.0] * 5, _dates(4), horizon_days=1)
    with pytest.raises(ValueError, match="> 0"):
        expected_move([100.0, -1.0, 100.0, 100.0], _dates(4), horizon_days=1,
                      min_samples=2)
    with pytest.raises(ValueError, match="overlapping"):
        expected_move([100.0] * 10, _dates(10), horizon_days=5)  # 5 samples < 20


# --- tool + endpoint ----------------------------------------------------------

def _alternating_bars(n=60):
    closes = [100.0]
    for i in range(n - 1):
        closes.append(closes[-1] * (1.02 if i % 2 == 0 else 1 / 1.02))
    return {
        "symbol": "SPY",
        "next_page_token": None,
        "bars": [
            {"t": f"2026-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}T04:00:00Z",
             "o": c, "h": c, "l": c, "c": c, "v": 1}
            for i, c in enumerate(closes)
        ],
    }


def market_fake(bars_json: dict) -> MarketDataClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=bars_json)

    return MarketDataClient(settings=paper_settings(), transport=httpx.MockTransport(handler))


def test_get_expected_move_tool_executes():
    with market_fake(_alternating_bars()) as m:
        out = registry.execute("get_expected_move", {"symbol": "SPY"},
                               ToolContext(market=m))
    r = out["expected_move"]
    assert r["horizon_days"] == 5
    assert r["unconditional"]["samples"] == 55
    assert set(r["unconditional"]["percentiles"]) == {"p05", "p25", "p50", "p75", "p95"}
    assert r["unconditional"]["band_prices"]["p50"] > 0
    assert "NOT a forecast" in r["note"]
    assert out["source"] == "alpaca-data-iex" and out["asof"]


def test_get_expected_move_tool_rejects_thin_history():
    thin = _alternating_bars(10)
    with market_fake(thin) as m, pytest.raises(ToolError, match="overlapping"):
        registry.execute("get_expected_move", {"symbol": "SPY"}, ToolContext(market=m))


def test_expected_move_endpoint():
    from api import main as main_module

    def fake_client_dep():
        with market_fake(_alternating_bars()) as m:
            yield m

    app.dependency_overrides[main_module.get_market_client] = fake_client_dep
    try:
        r = client.get("/api/expected-move/SPY")
    finally:
        app.dependency_overrides.pop(main_module.get_market_client)
    assert r.status_code == 200
    body = r.json()
    assert body["expected_move"]["unconditional"]["samples"] == 55
    assert body["asof"]
