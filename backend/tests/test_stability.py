"""T092 stability sweeps — verdicts hand-verified on constructed sweep results."""

import json
import math

import httpx
import pytest
from test_alpaca import paper_settings

from backtest.ledger import attach_stability, run_and_record
from backtest.stability import (
    SUPPORT_MIN_FRAC,
    SUPPORT_TOLERANCE,
    SWEEPS,
    run_sweep,
    stability_report,
)
from backtest.strategies import TEMPLATES, build_strategy
from data.db import make_engine, make_session_factory
from data.market_data import MarketDataClient
from data.models import BacktestRun, Base

# --- pure verdicts ------------------------------------------------------------

def test_plateau_is_stable():
    # best 1.0 @50; every other point >= 0.5 (tolerance 0.5*1.0) -> support 1.0
    rep = stability_report("momentum", "lookback",
                           [(30, 0.8), (40, 0.9), (50, 1.0), (60, 0.95), (75, 0.85)])
    assert rep.verdict == "stable"
    assert rep.best_param == 50 and rep.best_metric == 1.0
    assert rep.support_frac == 1.0
    assert rep.median_metric == 0.9


def test_isolated_spike_is_curve_fit():
    # best 1.2 @50; others all < 0.6 -> support 0/4; median -0.05 -> curve_fit
    rep = stability_report("momentum", "lookback",
                           [(30, -0.2), (40, -0.1), (50, 1.2), (60, 0.0), (75, -0.3)])
    assert rep.verdict == "curve_fit"
    assert rep.support_frac == 0.0
    assert "isolated peak" in rep.note


def test_exactly_half_support_with_positive_median_is_stable():
    # best 1.0 @40; others: 0.5 (supports), 0.5 (supports), 0.1, 0.2 -> 2/4 = 0.5
    rep = stability_report("momentum", "lookback",
                           [(30, 0.5), (40, 1.0), (50, 0.5), (60, 0.1), (75, 0.2)])
    assert rep.support_frac == 0.5 == SUPPORT_MIN_FRAC
    assert rep.median_metric == 0.5
    assert rep.verdict == "stable"


def test_nothing_works_is_reject():
    rep = stability_report("momentum", "lookback",
                           [(30, -0.5), (50, -0.1), (75, -0.9)])
    assert rep.verdict == "reject"
    assert "works nowhere" in rep.note


def test_two_points_is_insufficient():
    rep = stability_report("momentum", "lookback", [(30, 1.0), (50, 1.0)])
    assert rep.verdict == "insufficient"


def test_positive_spike_negative_median_is_curve_fit():
    # support could pass but median <= 0 -> still curve_fit (edge must be broad)
    rep = stability_report("momentum", "lookback",
                           [(30, 0.6), (40, 1.0), (50, -0.4), (60, -0.5), (75, -0.6)])
    assert rep.median_metric == -0.4
    assert rep.verdict == "curve_fit"
    assert SUPPORT_TOLERANCE == 0.5  # doc anchor


# --- engine-backed sweep ------------------------------------------------------

def rising_history(n=320, drift=0.004):
    closes = [100.0]
    for i in range(n - 1):
        closes.append(closes[-1] * math.exp(drift + 0.002 * math.sin(i)))
    dates = [f"d{i}" for i in range(n)]
    return closes, dates


def test_sweep_on_steady_uptrend_is_stable():
    # every momentum lookback rides a persistent uptrend -> plateau, not spike
    closes, dates = rising_history()
    rep = run_sweep(closes, dates, "momentum", cost_bps=5.0, values=[20, 40, 60])
    assert len(rep.results) == 3
    assert rep.best_metric > 0
    assert rep.verdict == "stable"
    assert rep.param_name == "lookback"


def test_sweep_rows_carry_the_2x_cost_metric():
    """T109/D029: every sweep point reports its Sharpe at doubled costs beside
    the base metric — advisory context; the VERDICT stays a function of the
    base metric so previously recorded sweeps are not silently re-judged."""
    closes = [100.0 * (1.01 ** i) for i in range(160)]
    dates = [f"2026-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}" for i in range(160)]
    rep = run_sweep(closes, dates, "momentum", cost_bps=5.0)
    assert rep.results, "sweep produced no rows"
    for row in rep.results:
        assert "metric_2x_cost" in row
        assert isinstance(row["metric_2x_cost"], float)
    # Same sweep judged at base costs only — verdict must be identical.
    rep_base = run_sweep(closes, dates, "momentum", cost_bps=5.0)
    assert rep.verdict == rep_base.verdict


def test_sweep_never_invested_params_score_zero_with_warning():
    closes, dates = rising_history(n=60)
    # lookback 90 > history: never invests -> constant curve -> 0.0 + warning
    rep = run_sweep(closes, dates, "momentum", values=[10, 20, 90])
    zero = [r for r in rep.results if r["param"] == 90][0]
    assert zero["metric"] == 0.0
    assert any("never invested" in w for w in rep.warnings)


def test_sweep_unknown_template_rejected():
    with pytest.raises(ValueError) as exc:
        run_sweep([1, 2, 3], ["a", "b", "c"], "buy_and_hold")
    assert "not sweepable" in str(exc.value)


def test_every_sweepable_template_exists_in_registry():
    assert set(SWEEPS) <= set(TEMPLATES)
    for name in SWEEPS:
        build_strategy(name)  # constructs without error


# --- ledger attachment --------------------------------------------------------

def bars_json(n=120):
    closes, _ = rising_history(n)
    return {"symbol": "SPY", "next_page_token": None,
            "bars": [{"t": f"2026-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}T04:00:00Z",
                      "o": 1, "h": 1, "l": 1, "c": c, "v": 1}
                     for i, c in enumerate(closes)]}


def test_attach_stability_lands_on_the_template_run():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    market = MarketDataClient(
        settings=paper_settings(),
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=bars_json())),
    )
    with make_session_factory(engine)() as db, market:
        run_and_record(db, market, build_strategy("momentum"),
                       {"template": "momentum"}, "SPY", days=120)
        closes, dates = rising_history(120)
        rep = run_sweep(closes, dates, "momentum", values=[20, 40, 60])
        from dataclasses import asdict
        run_id = attach_stability(db, "momentum", "spy", asdict(rep))
        row = db.get(BacktestRun, run_id)
        stored = json.loads(row.stability_json)
        assert stored["verdict"] == rep.verdict
        assert stored["param_name"] == "lookback"
        # attaching to a template with no runs fails loudly
        with pytest.raises(ValueError):
            attach_stability(db, "range", "SPY", asdict(rep))
    engine.dispose()
