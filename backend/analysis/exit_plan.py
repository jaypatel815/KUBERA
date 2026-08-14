"""Structured exit plans (T056) — "how long do I hold?" as data, not prose.

The doctrine's answer depends on WHY you're in the trade, so the plan is keyed to
the regime thesis (long-only owner):

- range:     enter the edges; TARGET the far edge; a CLOSE below support kills
             the thesis; re-examine on a time fallback even if neither edge hits.
- trend_up:  trends are RIDDEN, not targeted — no fixed target; invalidation is
             the trend-break level (the SMA the classifier used, or the swing
             support); review on a short cadence while structure holds.
- trend_down (long-only): the exit IS the plan — no long thesis exists.
- breakout:  hold only while price stays beyond the broken boundary; a close
             back inside means the fakeout completed; judge within the T053
             hold-confirmation window.
- coil (breakout_watch, no live escape): the range plan applies, with the note
             that the coming expansion picks the real plan.

Everything is a number or a dated fact the chat layer narrates — invalidation,
target, review horizon, stop distance in ATRs, reward/risk when both ends exist.
Bad input raises ValueError (fail closed).
"""

from dataclasses import dataclass

from analysis.confluence import REGIMES


@dataclass(frozen=True)
class ExitPlan:
    thesis_type: str  # "range" | "trend_up" | "trend_down_exit" | "breakout" | "coil"
    invalidation_level: float | None   # a CLOSE beyond this kills the thesis
    invalidation_reason: str
    target_level: float | None         # None for trends — ridden, not targeted
    target_reason: str
    review_horizon_days: int           # re-examine by then regardless of price
    review_reason: str
    stop_distance_atr: float | None    # (close - invalidation)/ATR, sizing context
    reward_risk: float | None          # (target-close)/(close-invalidation)
    notes: list[str]


def build_exit_plan(
    regime: str,
    last_close: float,
    *,
    atr_value: float | None = None,
    support: float | None = None,
    resistance: float | None = None,
    sma: float | None = None,
    breakout_boundary: float | None = None,
    breakout_direction: str | None = None,
    expected_move_p95: float | None = None,  # horizon-return fraction, e.g. 0.05
    hold_confirm_days: int = 2,
) -> ExitPlan:
    if regime not in REGIMES:
        raise ValueError(f"regime must be one of {REGIMES}, got {regime!r}")
    if last_close <= 0:
        raise ValueError("last_close must be > 0")
    for name, v in (("atr_value", atr_value), ("support", support),
                    ("resistance", resistance), ("sma", sma),
                    ("breakout_boundary", breakout_boundary)):
        if v is not None and v <= 0:
            raise ValueError(f"{name} must be > 0 when provided")

    notes: list[str] = []

    if regime == "trending_down":
        return ExitPlan(
            thesis_type="trend_down_exit",
            invalidation_level=None,
            invalidation_reason="no long thesis exists in a downtrend (long-only)",
            target_level=None,
            target_reason="the exit is the plan",
            review_horizon_days=1,
            review_reason="if held, reduce on strength — review daily until flat",
            stop_distance_atr=None,
            reward_risk=None,
            notes=["long-only account: downtrend structure means the plan is the "
                   "exit, not a hold"],
        )

    if regime == "trending_up":
        candidates = [v for v in (sma, support) if v is not None and v < last_close]
        invalidation = max(candidates) if candidates else None
        if expected_move_p95 is not None:
            notes.append(
                f"review point (not a target): {last_close * (1 + expected_move_p95):.2f} "
                "— the p95 of the historical move band"
            )
        notes.append("trends are ridden, not targeted — exit on structure break, "
                     "not on a number hit")
        return _finish(
            "trend_up", last_close, atr_value, invalidation,
            "a CLOSE below the trend-break level (20-bar average / swing support) "
            "ends the trend thesis",
            None, "no fixed target in a trend",
            5, "re-examine structure every 5 sessions while the trend holds", notes,
        )

    if regime == "breakout_watch" and breakout_boundary is not None:
        direction = breakout_direction or "up"
        if direction == "up":
            notes.append("hold is only valid while the break holds — volume "
                         "confirmation matters (see get_breakouts)")
            return _finish(
                "breakout", last_close, atr_value, breakout_boundary,
                "a CLOSE back inside the broken boundary = the fakeout completed",
                None, "measured targets come after the hold confirms",
                hold_confirm_days,
                f"judge the hold within {hold_confirm_days} sessions of the break",
                notes,
            )
        return ExitPlan(
            thesis_type="breakout", invalidation_level=None,
            invalidation_reason="downside break: no long thesis (long-only)",
            target_level=None, target_reason="the exit is the plan",
            review_horizon_days=1, review_reason="downside break in progress",
            stop_distance_atr=None, reward_risk=None,
            notes=["downside breakout: for a long-only account this is exit "
                   "information, not an entry"],
        )

    # range_bound, or a coiled breakout_watch with no live escape
    thesis = "range" if regime == "range_bound" else "coil"
    if thesis == "coil":
        notes.append("coiled range: the expansion direction picks the real plan — "
                     "this is the pre-break posture")
    if support is not None and resistance is not None and support < resistance:
        span = resistance - support
        pos = (last_close - support) / span
        if 0.3 <= pos <= 0.7:
            notes.append(f"price is mid-range ({pos:.0%} of the span) — the worst "
                         "risk/reward zone; edges are where the trade is")
    return _finish(
        thesis, last_close, atr_value, support,
        "a CLOSE below support breaks the range floor and the thesis",
        resistance, "the far edge of the range — trade the edges",
        10 if thesis == "range" else 5,
        "ranges resolve or persist — re-examine on the clock, not just the price",
        notes,
    )


def _finish(thesis, close, atr_value, invalidation, inv_reason, target,
            target_reason, horizon, review_reason, notes) -> ExitPlan:
    stop_atr = None
    if invalidation is not None and atr_value and invalidation < close:
        stop_atr = (close - invalidation) / atr_value
    rr = None
    if (invalidation is not None and target is not None
            and invalidation < close < target):
        rr = (target - close) / (close - invalidation)
    return ExitPlan(
        thesis_type=thesis,
        invalidation_level=invalidation,
        invalidation_reason=inv_reason,
        target_level=target,
        target_reason=target_reason,
        review_horizon_days=horizon,
        review_reason=review_reason,
        stop_distance_atr=stop_atr,
        reward_risk=rr,
        notes=notes,
    )
