"""Position triage (T086, owner Q&A 2026-08-13) — you're IN the trade; now what?

The question behind "should I average down?" is really "is the thesis alive?",
and the T056 exit plan already encodes the answer. Triage applies it:

- invalidation CLOSED through, or the regime is a downtrend -> EXIT. Adding to a
  dead thesis is not "lowering your average" — it is increasing exposure to a
  losing idea, and this module will never phrase it otherwise.
- target reached (range theses) -> EXIT AT TARGET: the edge-to-edge trade is
  complete; wanting more is a NEW thesis, not this one.
- otherwise -> HOLD, with an explicit add-assessment:
    * range/coil theses: adding is legitimate ONLY at the edge (lower quarter of
      the invalidation->target span) — buy support, never mid-range — and the
      combined position must still fit the 1% risk budget (size_position knows).
    * trend theses: adds happen on STRENGTH (continuation, new structure), never
      on dips toward the break level — a dip toward invalidation is the market
      arguing with the thesis, not a discount.
- the review clock: if the plan's horizon has passed without resolution, triage
  flags it — re-run the plan, don't autopilot a stale thesis.

Pure function on injected values; the tool composes live data. ValueError on bad
input (fail closed).
"""

from dataclasses import dataclass

THESES = ("range", "trend_up", "trend_down_exit", "breakout", "coil")
EDGE_FRACTION = 0.25  # "at the edge" = lower quarter of the invalidation->target span

HONESTY_NOTE = (
    "adding while underwater increases exposure to a thesis that has not proven "
    "itself — it is NOT 'lowering your average'; if you add, the COMBINED position "
    "must still fit the risk budget (ask size_position)"
)


@dataclass(frozen=True)
class AddAssessment:
    allowed: bool
    reason: str
    honesty_note: str


@dataclass(frozen=True)
class TriageReading:
    verdict: str  # "exit" | "exit_at_target" | "hold"
    verdict_reason: str
    unrealized_frac: float
    review_due: bool
    add_assessment: AddAssessment
    distance_to_invalidation_frac: float | None  # (last - inv)/last; None if no inv
    distance_to_target_frac: float | None
    risk_remaining_atr: float | None  # (last - invalidation)/ATR
    notes: list[str]


def triage_position(
    entry_price: float,
    last_price: float,
    thesis_type: str,
    *,
    invalidation_level: float | None = None,
    target_level: float | None = None,
    review_horizon_days: int | None = None,
    days_held: int | None = None,
    atr_value: float | None = None,
) -> TriageReading:
    if thesis_type not in THESES:
        raise ValueError(f"thesis_type must be one of {THESES}, got {thesis_type!r}")
    if entry_price <= 0 or last_price <= 0:
        raise ValueError("prices must be > 0")
    for name, v in (("invalidation_level", invalidation_level),
                    ("target_level", target_level), ("atr_value", atr_value)):
        if v is not None and v <= 0:
            raise ValueError(f"{name} must be > 0 when provided")
    if days_held is not None and days_held < 0:
        raise ValueError("days_held must be >= 0")

    unrealized = last_price / entry_price - 1.0
    review_due = (review_horizon_days is not None and days_held is not None
                  and days_held >= review_horizon_days)
    notes: list[str] = []
    if review_due:
        notes.append(
            f"review clock expired ({days_held} sessions held vs a "
            f"{review_horizon_days}-session plan) — re-run the exit plan before "
            "doing anything else; a stale thesis is not a thesis"
        )

    no_add = AddAssessment(False, "adding is off the table for this verdict",
                           HONESTY_NOTE)

    # 1. dead thesis -> exit, full stop
    if thesis_type == "trend_down_exit":
        return _reading("exit", "downtrend structure: no long thesis exists "
                        "(long-only) — the exit is the plan",
                        unrealized, review_due, no_add,
                        invalidation_level, target_level, last_price, atr_value,
                        notes)
    if invalidation_level is not None and last_price <= invalidation_level:
        return _reading(
            "exit",
            f"price {last_price} is at/through the invalidation level "
            f"{invalidation_level} — the thesis is dead; adding here is increasing "
            "exposure to a losing idea, not lowering an average",
            unrealized, review_due, no_add,
            invalidation_level, target_level, last_price, atr_value, notes,
        )

    # 2. range target reached -> take the edge
    if target_level is not None and last_price >= target_level:
        return _reading(
            "exit_at_target",
            f"price {last_price} reached the target {target_level} — the "
            "edge-to-edge trade is complete; wanting more is a NEW thesis",
            unrealized, review_due, no_add,
            invalidation_level, target_level, last_price, atr_value, notes,
        )

    # 3. thesis alive -> hold, with the add question answered honestly
    if thesis_type in ("range", "coil"):
        if (invalidation_level is not None and target_level is not None
                and invalidation_level < target_level):
            span = target_level - invalidation_level
            pos = (last_price - invalidation_level) / span
            at_edge = pos <= EDGE_FRACTION
            add = AddAssessment(
                allowed=at_edge,
                reason=(f"price sits in the lower {pos:.0%} of the range span — "
                        "at the edge, where range entries belong" if at_edge else
                        f"price is {pos:.0%} up the range span — not the edge; "
                        "mid-range adds are the worst risk/reward"),
                honesty_note=HONESTY_NOTE,
            )
        else:
            add = AddAssessment(False, "range edges unknown — cannot bless an add",
                                HONESTY_NOTE)
    else:  # trend_up, breakout
        add = AddAssessment(
            allowed=False,
            reason=("trend adds happen on STRENGTH — continuation and new "
                    "structure — never on dips toward the break level; a dip "
                    "toward invalidation is the market arguing with the thesis"),
            honesty_note=HONESTY_NOTE,
        )

    if unrealized >= 0 and thesis_type in ("trend_up", "breakout"):
        notes.append("in profit with the trend intact: the exit plan's "
                     "invalidation may ratchet up with new swing lows — refresh it")

    return _reading(
        "hold",
        "thesis intact: price is above invalidation and below any target — the "
        "plan is doing its job",
        unrealized, review_due, add,
        invalidation_level, target_level, last_price, atr_value, notes,
    )


def _reading(verdict, reason, unrealized, review_due, add,
             invalidation, target, last, atr_value, notes) -> TriageReading:
    return TriageReading(
        verdict=verdict,
        verdict_reason=reason,
        unrealized_frac=unrealized,
        review_due=review_due,
        add_assessment=add,
        distance_to_invalidation_frac=(
            (last - invalidation) / last if invalidation is not None else None),
        distance_to_target_frac=(
            (target - last) / last if target is not None else None),
        risk_remaining_atr=(
            (last - invalidation) / atr_value
            if invalidation is not None and atr_value else None),
        notes=notes,
    )
