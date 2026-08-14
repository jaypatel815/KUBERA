"""Parameter stability sweeps (T092, D020) — the curve-fit detector.

A template that shines at lookback=60 but dies at 50 and 75 didn't find edge;
it memorized one path of history. Before trusting a promotion, sweep the
parameter neighborhood and demand a PLATEAU: most neighbors should retain a
meaningful share of the best result.

Verdicts (deterministic, hand-tested):
- "insufficient"  fewer than 3 sweep points — nothing can be concluded
- "reject"        best risk-adjusted result <= 0 — works nowhere
- "curve_fit"     isolated peak: neighbors don't hold >= SUPPORT_TOLERANCE of
                  the best, or the median across the sweep is <= 0
- "stable"        a plateau: >= SUPPORT_MIN_FRAC of the OTHER points hold
                  >= SUPPORT_TOLERANCE of the best AND the sweep median > 0

The metric is annualized Sharpe of the backtest equity curve (risk-adjusted so
a leverage-shaped fluke can't fake a plateau). Sharpe is undefined on constant
curves (never-invested strategies); those points enter the sweep as 0.0 — a
parameter that never trades supports nothing.
"""

import statistics
from dataclasses import dataclass, field, replace
from typing import Callable, Sequence

from analysis.metrics import daily_returns, sharpe
from backtest.engine import run_backtest
from backtest.strategies import (
    make_mean_reversion,
    make_momentum,
    make_range,
    make_sma_cross,
)

SUPPORT_TOLERANCE = 0.5   # a neighbor "supports" if it keeps >= 50% of the best
SUPPORT_MIN_FRAC = 0.5    # at least half the other points must support

# template -> (param name, default sweep values, builder)
SWEEPS: dict[str, tuple[str, list, Callable]] = {
    "momentum": ("lookback", [20, 30, 40, 50, 60, 75, 90],
                 lambda v: make_momentum(lookback=int(v))),
    "sma_cross": ("fast", [20, 30, 40, 50, 60, 80],
                  lambda v: make_sma_cross(fast=int(v), slow=200)),
    "mean_reversion": ("window", [10, 15, 20, 25, 30, 40],
                       lambda v: make_mean_reversion(window=int(v))),
    "range": ("lookback", [20, 30, 40, 50, 60],
              lambda v: make_range(lookback=int(v))),
}


@dataclass(frozen=True)
class StabilityReport:
    template: str
    param_name: str
    results: list          # [{param, metric}] in sweep order
    best_param: float
    best_metric: float
    median_metric: float
    support_frac: float    # fraction of OTHER points holding >= tolerance * best
    verdict: str           # insufficient | reject | curve_fit | stable
    note: str = ""
    warnings: list = field(default_factory=list)


def stability_report(template: str, param_name: str,
                     results: list[tuple[float, float]]) -> StabilityReport:
    """Pure verdict from (param, metric) pairs — the tested core."""
    rows = [{"param": p, "metric": m} for p, m in results]
    if len(results) < 3:
        return StabilityReport(
            template=template, param_name=param_name, results=rows,
            best_param=results[0][0] if results else float("nan"),
            best_metric=results[0][1] if results else float("nan"),
            median_metric=float("nan"), support_frac=0.0,
            verdict="insufficient",
            note="fewer than 3 sweep points — widen the sweep before judging",
        )
    best_param, best_metric = max(results, key=lambda r: r[1])
    metrics = [m for _, m in results]
    median_metric = statistics.median(metrics)
    if best_metric <= 0:
        return StabilityReport(
            template=template, param_name=param_name, results=rows,
            best_param=best_param, best_metric=best_metric,
            median_metric=median_metric, support_frac=0.0, verdict="reject",
            note="best risk-adjusted result is <= 0 — this template works "
                 "nowhere in the neighborhood on this history",
        )
    others = [m for p, m in results if p != best_param]
    support = sum(1 for m in others if m >= SUPPORT_TOLERANCE * best_metric)
    support_frac = round(support / len(others), 4) if others else 0.0
    stable = support_frac >= SUPPORT_MIN_FRAC and median_metric > 0
    return StabilityReport(
        template=template, param_name=param_name, results=rows,
        best_param=best_param, best_metric=round(best_metric, 4),
        median_metric=round(median_metric, 4), support_frac=support_frac,
        verdict="stable" if stable else "curve_fit",
        note=("plateau: the edge survives away from the best parameter"
              if stable else
              "isolated peak: performance collapses off the best parameter — "
              "treat the backtest as curve-fit, not edge"),
    )


def run_sweep(closes: Sequence[float], dates: Sequence[str], template: str,
              cost_bps: float = 5.0, values: list | None = None) -> StabilityReport:
    """Sweep a template's parameter neighborhood on ONE price history.
    Engine-only — nothing is written to the ledger here (no run spam)."""
    if template not in SWEEPS:
        raise ValueError(
            f"template '{template}' is not sweepable — valid: "
            f"{', '.join(sorted(SWEEPS))}"
        )
    param_name, default_values, builder = SWEEPS[template]
    warnings: list[str] = []
    results: list[tuple[float, float]] = []
    for v in (values if values is not None else default_values):
        strategy = builder(v)
        res = run_backtest(closes, dates, strategy,
                           strategy_name=strategy.__name__, cost_bps=cost_bps)
        rets = daily_returns(res.equity_curve)
        try:
            metric = sharpe(rets)
        except ValueError:
            metric = 0.0   # never traded / constant curve: supports nothing
            warnings.append(f"{param_name}={v}: constant equity curve "
                            "(never invested) — metric set to 0")
        results.append((v, round(metric, 4)))
    return replace(stability_report(template, param_name, results),
                   warnings=warnings)
