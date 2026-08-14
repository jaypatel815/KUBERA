"""Goal math (I012) — every number here was computed by hand before the code ran.

The headline table (required CAGR for $1,000 → $1,000,000):
    10y: 1000^(1/10) - 1 = 10^0.3  - 1 ≈ 0.995262  (99.5%/yr)
    15y: 10^0.2  - 1 ≈ 0.584893
    20y: 10^0.15 - 1 ≈ 0.412538
    25y: 10^0.12 - 1 ≈ 0.318257
    30y: 10^0.1  - 1 ≈ 0.258925
And the reality check: 1.02^252 ≈ 146.98 — "2% a day" is a 147x year.
"""

import pytest
from fastapi.testclient import TestClient

from analysis.goal_math import (
    daily_return_reality,
    future_value,
    goal_scenarios,
    required_cagr,
    years_to_target,
)
from api.main import app
from api.tools import ToolContext, ToolError, registry

client = TestClient(app)


# --- required_cagr ------------------------------------------------------------

@pytest.mark.parametrize("years,expected", [
    (10, 0.995262), (15, 0.584893), (20, 0.412538),
    (25, 0.318257), (30, 0.258925),
])
def test_required_cagr_owner_headline_table(years, expected):
    got = required_cagr(1000, 1_000_000, years)
    assert got == pytest.approx(expected, rel=1e-4)
    # round trip: growing start at that rate for `years` lands on target
    assert 1000 * (1 + got) ** years == pytest.approx(1_000_000, rel=1e-9)


def test_required_cagr_rejects_nonsense():
    for bad in [(0, 1, 1), (1, 0, 1), (1, 1, 0), (-5, 10, 3)]:
        with pytest.raises(ValueError):
            required_cagr(*bad)


# --- future_value -------------------------------------------------------------

def test_fv_lump_sum_only_is_pure_compounding():
    # monthly rate constructed so (1+r)^12 == 1.10 exactly -> 1.1^10 = 2.59374246
    assert future_value(1000, 0, 10, 0.10) == pytest.approx(2593.74246, rel=1e-6)


def test_fv_zero_rate_is_simple_sum():
    assert future_value(0, 100, 1, 0.0) == pytest.approx(1200.0)
    assert future_value(500, 100, 2, 0.0) == pytest.approx(500 + 2400)


def test_fv_annuity_hand_check():
    # 12 months of $100 at 10%/yr: fv = 100 * (1.1 - 1)/r, r = 1.1^(1/12)-1
    # = 10 / 0.0079741404 = 1254.05
    assert future_value(0, 100, 1, 0.10) == pytest.approx(1254.05, rel=1e-4)


def test_fv_rejects_nonsense():
    with pytest.raises(ValueError):
        future_value(-1, 0, 1, 0.1)
    with pytest.raises(ValueError):
        future_value(0, -1, 1, 0.1)
    with pytest.raises(ValueError):
        future_value(1, 1, 0, 0.1)
    with pytest.raises(ValueError):
        future_value(1, 1, 1, -1.0)


# --- years_to_target ----------------------------------------------------------

def test_ytt_doubling_at_ten_percent():
    # need (1+r)^n >= 2, n >= ln2/ln(1.1^(1/12)) = 87.27 -> 88 months -> 7.3y
    assert years_to_target(1000, 0, 0.10, 2000) == 7.3


def test_ytt_owner_scenario_500_monthly():
    # 1000 start + $500/mo at 10%: crosses $1M in month 355 -> 29.6 years
    assert years_to_target(1000, 500, 0.10, 1_000_000) == 29.6


def test_ytt_honest_none_when_unreachable():
    assert years_to_target(1000, 0, 0.0, 1_000_000) is None  # flat forever


def test_ytt_already_there_is_zero():
    assert years_to_target(2000, 0, 0.10, 1000) == 0.0


# --- daily-compounding reality check ------------------------------------------

def test_two_percent_a_day_is_a_147x_year():
    out = daily_return_reality(0.02)
    assert out["annual_multiple"] == pytest.approx(146.98, rel=1e-3)
    assert "broken arithmetic" in out["note"]


def test_five_percent_a_day_is_absurd():
    assert daily_return_reality(0.05)["annual_multiple"] > 100_000


# --- scenario pack ------------------------------------------------------------

def test_goal_scenarios_shape_and_content():
    s = goal_scenarios(1000, 1_000_000)
    assert s.required_cagr_by_years["10"] == pytest.approx(0.995262, rel=1e-4)
    assert set(s.fv_table.keys()) == {"0", "50", "100", "250", "500"}
    assert set(s.fv_table["500"].keys()) == {"5%", "8%", "10%", "15%", "20%"}
    # $500/mo at 10% for 30y ~= $1.05M (contributions dominate the $1k start)
    assert s.fv_table["500"]["10%"]["30"] == pytest.approx(1_048_000, rel=0.01)
    # $0/mo at 5%: never reaches $1M within a century
    assert s.years_to_target_table["0"]["5%"] is None
    assert s.years_to_target_table["500"]["10%"] == 29.6
    assert len(s.daily_reality) == 2
    assert "100 years" in s.note


def test_goal_scenarios_rejects_target_below_start():
    with pytest.raises(ValueError):
        goal_scenarios(1000, 500)


# --- tool + endpoint ----------------------------------------------------------

def test_goal_math_tool_needs_no_context():
    out = registry.execute(
        "goal_math", {"start": 1000, "target": 1_000_000}, ToolContext(),
    )
    assert out["source"] == "deterministic-math"
    assert out["scenarios"]["required_cagr_by_years"]["30"] == \
        pytest.approx(0.258925, rel=1e-4)


def test_goal_math_tool_rejects_inverted_goal():
    with pytest.raises(ToolError):
        registry.execute("goal_math", {"start": 1000, "target": 999}, ToolContext())


def test_goal_math_endpoint_defaults_to_owner_goal():
    r = client.get("/api/goal-math")
    assert r.status_code == 200
    body = r.json()
    assert body["scenarios"]["start"] == 1000.0
    assert body["scenarios"]["target"] == 1_000_000.0
    assert body["scenarios"]["required_cagr_by_years"]["20"] == \
        pytest.approx(0.412538, rel=1e-4)


def test_goal_math_endpoint_rejects_bad_goal():
    assert client.get("/api/goal-math?start=500&target=100").status_code == 422


# --- I012: the message that started all this must now fit ---------------------

def test_long_ips_message_passes_validation():
    from api.main import ChatRequest
    ChatRequest(message="x" * 19000, conversation_id=0)  # was 422 at 6k cap
    with pytest.raises(Exception):
        ChatRequest(message="x" * 20001, conversation_id=0)
