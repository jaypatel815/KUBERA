"""Strategy decay detection (T093, D021 gap 4) — earn the loop, KEEP earning it.

A promotion (T064) is evidence from the PAST. This module watches whether live
results keep honoring the backtest's expectation, with a one-sided CUSUM on
daily return shortfall:

    S_t = max(0, S_{t-1} + (mu_expected - r_t - k))

- mu_expected: the promoted run's mean daily return (its cumulative return
  spread over its bars — what the backtest implicitly promised).
- k (slack): expected noise allowance per day; small shortfalls don't count.
- h (threshold): sustained cumulative shortfall that triggers the alarm.

On alarm, `demote` flips the promoted ledger row to promotion_status="demoted",
and the paper loop's EXISTING require_promotion gate refuses new buys
automatically — no new code path, the gate just stops finding a passed run.

HONEST LIMITATION (label travels with every result): live per-strategy equity
does not exist yet at this account's fill volume, so the CLI compares against
ACCOUNT-level daily returns — a fair proxy only while one strategy trades the
account. The math here is strategy-agnostic and tested; the proxy is labeled.
"""

import json
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from data.models import BacktestRun

DEFAULT_SLACK_DAILY = 0.0005   # 5 bps/day of forgiven shortfall
DEFAULT_THRESHOLD = 0.05       # alarm after ~5% cumulative unforgiven shortfall
ACCOUNT_PROXY_NOTE = ("compared against ACCOUNT-level returns — a fair proxy "
                      "only while a single strategy trades this account")


def expected_daily_return(cumulative_return: float, bars_count: int) -> float:
    """The backtest's implicit daily promise: geometric mean daily return."""
    if bars_count < 2:
        raise ValueError("need at least 2 bars")
    if cumulative_return <= -1:
        raise ValueError("cumulative_return must be > -100%")
    return (1.0 + cumulative_return) ** (1.0 / (bars_count - 1)) - 1.0


@dataclass(frozen=True)
class CusumResult:
    alarm: bool
    stat: float                 # final CUSUM statistic
    peak: float
    crossed_at: int | None      # index (day) of first crossing, None if never
    mu_expected: float
    slack: float
    threshold: float
    n_days: int
    series: list = field(default_factory=list)  # S_t per day (for plotting)


def cusum_shortfall(live_returns: list[float], mu_expected: float,
                    slack: float = DEFAULT_SLACK_DAILY,
                    threshold: float = DEFAULT_THRESHOLD) -> CusumResult:
    """One-sided CUSUM of (expectation - reality - slack). Deterministic."""
    if slack < 0 or threshold <= 0:
        raise ValueError("slack must be >= 0, threshold > 0")
    s = 0.0
    peak = 0.0
    crossed = None
    series = []
    for i, r in enumerate(live_returns):
        s = max(0.0, s + (mu_expected - r - slack))
        series.append(round(s, 6))
        peak = max(peak, s)
        if crossed is None and s > threshold:
            crossed = i
    return CusumResult(
        alarm=crossed is not None, stat=round(s, 6), peak=round(peak, 6),
        crossed_at=crossed, mu_expected=round(mu_expected, 6), slack=slack,
        threshold=threshold, n_days=len(live_returns), series=series,
    )


def demote(session: Session, template: str, symbol: str, reason: str) -> int:
    """Flip the (template, symbol) pair's passed run(s) to 'demoted'. The paper
    loop's require_promotion gate then refuses new buys automatically. Returns
    the number of rows demoted; raises if none were promoted."""
    rows = session.execute(
        select(BacktestRun).where(
            BacktestRun.symbol == symbol.upper(),
            BacktestRun.promotion_status == "passed_walk_forward",
        )
    ).scalars().all()
    demoted = 0
    for r in rows:
        try:
            if json.loads(r.params_json).get("template") != template:
                continue
        except (TypeError, ValueError):
            continue
        r.promotion_status = "demoted"
        params = json.loads(r.params_json)
        params["demotion_reason"] = reason
        r.params_json = json.dumps(params, sort_keys=True)
        demoted += 1
    if demoted == 0:
        raise ValueError(
            f"no promoted run for template={template} symbol={symbol.upper()} — "
            "nothing to demote"
        )
    session.commit()
    return demoted
