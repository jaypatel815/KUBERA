"""Position triage (T086) — every verdict branch hand-computed; the averaging-down
honesty note is asserted, not assumed; plus the tool/endpoint."""

from datetime import datetime, timezone

import httpx
import pytest
from fastapi.testclient import TestClient
from test_alpaca import paper_settings

from analysis.triage import triage_position
from api.main import app
from api.tools import ToolContext, registry
from data.market_data import MarketDataClient

client = TestClient(app)


def test_invalidation_hit_means_exit_not_add():
    r = triage_position(100.0, 94.0, "range",
                        invalidation_level=95.0, target_level=110.0)
    assert r.verdict == "exit"
    assert "thesis is dead" in r.verdict_reason
    assert "increasing exposure" in r.verdict_reason  # never "lowering an average"
    assert r.unrealized_frac == pytest.approx(-0.06)
    assert r.add_assessment.allowed is False


def test_downtrend_is_always_exit():
    r = triage_position(100.0, 102.0, "trend_down_exit")
    assert r.verdict == "exit" and "long-only" in r.verdict_reason


def test_range_target_reached_is_the_full_edge():
    r = triage_position(96.0, 110.0, "range",
                        invalidation_level=95.0, target_level=110.0)
    assert r.verdict == "exit_at_target"
    assert "NEW thesis" in r.verdict_reason
    assert r.unrealized_frac == pytest.approx(110.0 / 96.0 - 1.0)


def test_underwater_range_add_allowed_only_at_the_edge():
    # span 95->110; last 96 sits at 6.7% of the span: the edge -> add allowed
    r = triage_position(100.0, 96.0, "range",
                        invalidation_level=95.0, target_level=110.0, atr_value=2.0)
    assert r.verdict == "hold"
    assert r.add_assessment.allowed is True
    assert "edge" in r.add_assessment.reason
    assert "NOT 'lowering your average'" in r.add_assessment.honesty_note
    assert r.risk_remaining_atr == pytest.approx(0.5)  # (96-95)/2

    # last 103 sits 53% up the span: mid-range -> no add
    mid = triage_position(100.0, 103.0, "range",
                          invalidation_level=95.0, target_level=110.0)
    assert mid.add_assessment.allowed is False
    assert "worst risk/reward" in mid.add_assessment.reason


def test_underwater_trend_never_blesses_the_dip():
    r = triage_position(100.0, 97.0, "trend_up", invalidation_level=96.0)
    assert r.verdict == "hold"
    assert r.add_assessment.allowed is False
    assert "on STRENGTH" in r.add_assessment.reason
    assert "arguing with the thesis" in r.add_assessment.reason


def test_profitable_trend_suggests_refreshing_the_plan():
    r = triage_position(100.0, 108.0, "trend_up", invalidation_level=96.0)
    assert r.verdict == "hold"
    assert any("ratchet up" in n for n in r.notes)


def test_review_clock_expiry_is_flagged():
    r = triage_position(100.0, 101.0, "range", invalidation_level=95.0,
                        target_level=110.0, review_horizon_days=10, days_held=12)
    assert r.review_due is True
    assert any("stale thesis" in n for n in r.notes)


def test_validation():
    with pytest.raises(ValueError, match="thesis_type"):
        triage_position(100.0, 100.0, "yolo")
    with pytest.raises(ValueError, match="prices"):
        triage_position(0.0, 100.0, "range")
    with pytest.raises(ValueError, match="days_held"):
        triage_position(100.0, 100.0, "range", days_held=-1)


# --- tool + endpoint (trending sawtooth; entry above current -> hold, no add) --

def _sawtooth_json(n=100):
    closes = [100.0]
    factors = [1.02, 1.02, 1.02, 1.02, 0.97]
    for i in range(n - 1):
        closes.append(closes[-1] * factors[i % 5])
    return closes, {"symbol": "SPY", "next_page_token": None, "bars": [
        {"t": f"2026-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}T04:00:00Z",
         "o": c, "h": c * 1.002, "l": c * 0.998, "c": c, "v": 1_000_000}
        for i, c in enumerate(closes)
    ]}


def market_fake(last_close):
    _, bars_json = _sawtooth_json()

    def handler(request: httpx.Request) -> httpx.Response:
        if "/trades/latest" in request.url.path:
            return httpx.Response(200, json={
                "symbol": "SPY",
                "trade": {"t": datetime.now(timezone.utc).isoformat(),
                          "p": last_close, "s": 1}})
        return httpx.Response(200, json=bars_json)

    return MarketDataClient(settings=paper_settings(), transport=httpx.MockTransport(handler))


def test_triage_tool_full_stack():
    closes, _ = _sawtooth_json()
    last = closes[-1]
    with market_fake(last) as m:
        out = registry.execute(
            "triage_position",
            {"symbol": "SPY", "entry_price": last * 1.05, "days_held": 2},
            ToolContext(market=m),
        )
    assert out["regime"] == "trending_up"
    t = out["triage"]
    assert t["verdict"] == "hold"  # underwater but above invalidation
    assert t["unrealized_frac"] == pytest.approx(1 / 1.05 - 1, abs=1e-6)
    assert t["add_assessment"]["allowed"] is False  # trend dip: never blessed
    assert out["exit_plan"]["thesis_type"] == "trend_up"


def test_triage_endpoint():
    from api import main as main_module

    closes, _ = _sawtooth_json()

    def fake_market():
        with market_fake(closes[-1]) as m:
            yield m

    app.dependency_overrides[main_module.get_market_client] = fake_market
    try:
        r = client.get("/api/triage/SPY", params={"entry_price": closes[-1] * 0.9})
    finally:
        app.dependency_overrides.pop(main_module.get_market_client)
    assert r.status_code == 200
    body = r.json()
    assert body["triage"]["verdict"] == "hold"  # in profit, trend intact
    assert body["triage"]["unrealized_frac"] > 0
