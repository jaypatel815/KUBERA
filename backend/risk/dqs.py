"""Decision Quality Score v1 (T067, D014) — process over outcome.

Scores the recent TRADING PATTERN in signal_log, not P&L: a disciplined loss
scores better than a lucky rule-break. v1 HONESTY: this scores the paper loop's
recorded activity; scoring the owner's own manual fills needs T036/T016 sync and
the T063 journal (follow/override tracking) — say so, don't pretend.

Components (each deterministic, hand-computable, capped):
- trade_frequency  penalty up to 40: average orders/day vs max_trades_per_day —
  penalty = min(40, max(0, (avg_per_day / max_per_day - 0.6) * 100)).
  Running at 60% of the overtrading guard is free; beyond that it costs.
- post_loss_activity  penalty up to 30: share of orders placed while equity sat
  below the previous logged row's equity (a deterministic "trading into
  drawdown" proxy) — penalty = min(30, frac * 40).
- sizing_consistency  penalty up to 30: coefficient of variation of order
  deltas |target - current| — penalty = min(30, max(0, (cv - 0.5) * 30)).
  Wild size swings are the signature of emotional sizing.
- restraint (informational, no score effect): count of no_trade decisions —
  evidence the system concluded "nothing today" and honored it.

Score = 100 - penalties, floored at 0. No activity = 100 with a note.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from statistics import mean, stdev
from typing import Sequence


@dataclass(frozen=True)
class DQSReport:
    score: float
    window_days: int
    orders: int
    no_trades: int
    components: dict[str, dict]
    note: str


def score_decisions(
    rows: Sequence,
    *,
    max_trades_per_day: int = 5,
    window_days: int = 7,
    now: datetime | None = None,
) -> DQSReport:
    """Rows: any objects with .ts, .action, .equity, .target_value, .current_value
    (SignalLog satisfies this). Rows outside the window are ignored."""
    if max_trades_per_day < 1 or window_days < 1:
        raise ValueError("max_trades_per_day and window_days must be >= 1")
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=window_days)

    def _ts(row):
        ts = row.ts
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)

    recent = sorted((r for r in rows if _ts(r) >= cutoff), key=_ts)
    ordered = [r for r in recent if r.action == "ordered"]
    no_trades = sum(1 for r in recent if r.action == "no_trade")

    if not ordered:
        return DQSReport(
            score=100.0, window_days=window_days, orders=0, no_trades=no_trades,
            components={},
            note="no orders in the window — no activity, no bad habits to score",
        )

    # trade frequency vs the overtrading guard
    active_days = len({_ts(r).date() for r in ordered})
    avg_per_day = len(ordered) / active_days
    freq_ratio = avg_per_day / max_trades_per_day
    p_freq = min(40.0, max(0.0, (freq_ratio - 0.6) * 100.0))

    # trading into drawdown: order placed while equity below the previous row's
    post_loss = 0
    for i, row in enumerate(recent):
        if row.action != "ordered" or i == 0:
            continue
        if row.equity < recent[i - 1].equity:
            post_loss += 1
    post_loss_frac = post_loss / len(ordered)
    p_loss = min(30.0, post_loss_frac * 40.0)

    # sizing consistency
    deltas = [abs(r.target_value - r.current_value) for r in ordered]
    if len(deltas) >= 2 and mean(deltas) > 0:
        cv = stdev(deltas) / mean(deltas)
    else:
        cv = 0.0
    p_sizing = min(30.0, max(0.0, (cv - 0.5) * 30.0))

    score = max(0.0, round(100.0 - p_freq - p_loss - p_sizing, 1))
    return DQSReport(
        score=score,
        window_days=window_days,
        orders=len(ordered),
        no_trades=no_trades,
        components={
            "trade_frequency": {
                "penalty": round(p_freq, 1), "avg_orders_per_day": round(avg_per_day, 2),
                "max_per_day": max_trades_per_day,
            },
            "post_loss_activity": {
                "penalty": round(p_loss, 1), "orders_into_drawdown": post_loss,
                "frac": round(post_loss_frac, 3),
            },
            "sizing_consistency": {
                "penalty": round(p_sizing, 1), "cv": round(cv, 3),
            },
            "restraint": {
                "penalty": 0.0, "no_trade_decisions": no_trades,
                "note": "restraint is free — cash was a decision, not a failure",
            },
        },
        note=(
            "v1 scores the paper loop's recorded pattern (process, not P&L). "
            "Scoring your own fills arrives with the broker-fill sync and the "
            "decision journal."
        ),
    )
