"""Exit plans (T056) — every thesis branch hand-computed + the tool/endpoint."""

import httpx
import pytest
from fastapi.testclient import TestClient
from test_alpaca import paper_settings

from analysis.exit_plan import build_exit_plan
from api.main import app
from api.tools import ToolContext, registry
from data.market_data import MarketDataClient

client = TestClient(app)


def test_range_plan_hand():
    # close 100 between support 95 and resistance 110, ATR 2:
    # stop distance (100-95)/2 = 2.5 ATRs; RR = 10/5 = 2.0
    p = build_exit_plan("range_bound", 100.0, atr_value=2.0,
                        support=95.0, resistance=110.0)
    assert p.thesis_type == "range"
    assert p.invalidation_level == pytest.approx(95.0)
    assert p.target_level == pytest.approx(110.0)
    assert p.stop_distance_atr == pytest.approx(2.5)
    assert p.reward_risk == pytest.approx(2.0)
    assert p.review_horizon_days == 10
    assert any("mid-range" in n for n in p.notes)  # 33% of span: worst-RR warning


def test_range_edge_entry_has_no_midrange_warning():
    p = build_exit_plan("range_bound", 95.5, support=95.0, resistance=110.0)
    assert not any("mid-range" in n for n in p.notes)


def test_trend_up_is_ridden_not_targeted():
    p = build_exit_plan("trending_up", 100.0, atr_value=2.0,
                        support=92.0, sma=96.0, expected_move_p95=0.05)
    assert p.thesis_type == "trend_up"
    assert p.invalidation_level == pytest.approx(96.0)  # max(sma, support) below close
    assert p.target_level is None
    assert p.stop_distance_atr == pytest.approx(2.0)
    assert p.reward_risk is None
    assert any("105.00" in n for n in p.notes)  # p95 review point, not a target
    assert any("ridden, not targeted" in n for n in p.notes)


def test_trend_down_the_exit_is_the_plan():
    p = build_exit_plan("trending_down", 100.0, atr_value=2.0, support=95.0)
    assert p.thesis_type == "trend_down_exit"
    assert p.invalidation_level is None and p.target_level is None
    assert p.review_horizon_days == 1
    assert any("long-only" in n for n in p.notes)


def test_breakout_holds_the_boundary():
    p = build_exit_plan("breakout_watch", 105.0, atr_value=2.0,
                        breakout_boundary=100.5, breakout_direction="up")
    assert p.thesis_type == "breakout"
    assert p.invalidation_level == pytest.approx(100.5)
    assert "fakeout completed" in p.invalidation_reason
    assert p.review_horizon_days == 2  # the T053 hold-confirmation window
    assert p.stop_distance_atr == pytest.approx((105.0 - 100.5) / 2.0)


def test_downside_break_is_exit_information():
    p = build_exit_plan("breakout_watch", 95.0, breakout_boundary=100.0,
                        breakout_direction="down")
    assert p.thesis_type == "breakout" and p.invalidation_level is None
    assert any("exit" in n for n in p.notes)


def test_coil_uses_range_plan_with_expansion_note():
    p = build_exit_plan("breakout_watch", 100.0, support=99.0, resistance=101.0)
    assert p.thesis_type == "coil"
    assert p.invalidation_level == pytest.approx(99.0)
    assert p.review_horizon_days == 5
    assert any("expansion direction" in n for n in p.notes)


def test_stale_levels_never_crash_rr():
    # target below close (stale resistance): RR must be None, not negative
    p = build_exit_plan("range_bound", 100.0, support=90.0, resistance=98.0)
    assert p.reward_risk is None


def test_validation():
    with pytest.raises(ValueError, match="regime"):
        build_exit_plan("sideways", 100.0)
    with pytest.raises(ValueError, match="last_close"):
        build_exit_plan("range_bound", 0.0)
    with pytest.raises(ValueError, match="support"):
        build_exit_plan("range_bound", 100.0, support=-5.0)


# --- tool + endpoint (trending sawtooth: trend_up plan) -----------------------

def _sawtooth_json(n=100):
    closes = [100.0]
    factors = [1.02, 1.02, 1.02, 1.02, 0.97]
    for i in range(n - 1):
        closes.append(closes[-1] * factors[i % 5])
    return {"symbol": "SPY", "next_page_token": None, "bars": [
        {"t": f"2026-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}T04:00:00Z",
         "o": c, "h": c * 1.002, "l": c * 0.998, "c": c, "v": 1_000_000}
        for i, c in enumerate(closes)
    ]}


def market_fake() -> MarketDataClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_sawtooth_json())

    return MarketDataClient(settings=paper_settings(), transport=httpx.MockTransport(handler))


def test_get_exit_plan_tool_full_stack():
    with market_fake() as m:
        out = registry.execute("get_exit_plan", {"symbol": "SPY"}, ToolContext(market=m))
    assert out["regime"] == "trending_up"
    plan = out["exit_plan"]
    assert plan["thesis_type"] == "trend_up"
    assert plan["invalidation_level"] is not None
    assert plan["invalidation_level"] < out["last_close"]
    assert plan["target_level"] is None  # ridden, not targeted
    assert plan["stop_distance_atr"] is not None
    assert out["as_of_date"] and out["asof"]


def test_exit_plan_endpoint():
    from api import main as main_module

    def fake_market():
        with market_fake() as m:
            yield m

    app.dependency_overrides[main_module.get_market_client] = fake_market
    try:
        r = client.get("/api/exit-plan/SPY")
    finally:
        app.dependency_overrides.pop(main_module.get_market_client)
    assert r.status_code == 200
    assert r.json()["exit_plan"]["thesis_type"] == "trend_up"
