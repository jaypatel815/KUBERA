"""T063b — journal calibration v2 (pure, deterministic, hand-computable).

Three questions v1's single hit-rate cannot answer:
  1. CONFIDENCE CURVE — when KUBERA says 0.7, is it right ~70% of the time?
     Evaluable decisions bucket by STATED confidence; each bucket reports
     hit rate vs average stated confidence and the GAP between them.
     A bucket under MIN_PER_BUCKET is LISTED with its n and refuses a rate —
     thin data is named, never silently averaged (T069 discipline).
  2. PAYOFF vs PLAN — the stated target/stop define a planned R multiple
     (reward per unit of planned risk); the realized R is measured against
     the SAME stop distance. Endpoint-only, and the note says so: the
     journal has no price path, so max-adverse-excursion is unknowable here
     (live MAE/MFE is T089's job). A stop on the wrong side of entry is
     counted INVALID GEOMETRY by name, not skipped silently.
  3. OVERRIDE × OUTCOME (feeds T067b) — among aged decisions, how did the
     ones the owner FOLLOWED do versus the ones the owner OVERRODE?
     A high hit rate on overridden calls is coaching evidence, stated as
     process measurement, never as an I-told-you-so.

Evaluability matches v1 exactly (data/journal.summarize_decisions): a
direction verdict, an entry price, a horizon that has PASSED, and a live
price. Every exclusion is counted and visible. Any strategy-weight change
from these numbers remains a PROPOSAL the owner ratifies (ticket text).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable, Sequence

from data.journal import DIRECTION

MIN_PER_BUCKET = 5   # below this a bucket/group lists n and refuses a rate

# Stated-confidence bucket edges (last edge inclusive of 1.0). The persona
# caps stated confidence, so mass sits in the middle buckets by design.
BUCKET_EDGES = ((0.0, 0.5, "under 0.50"),
                (0.5, 0.65, "0.50-0.65"),
                (0.65, 0.8, "0.65-0.80"),
                (0.8, 1.0000001, "0.80+"))


@dataclass(frozen=True)
class ConfidenceBucket:
    label: str
    n: int
    hits: int
    avg_stated_confidence: float | None
    hit_rate: float | None       # None until n >= MIN_PER_BUCKET
    gap: float | None            # hit_rate - avg_stated (positive = underconfident)
    qualified: bool


@dataclass(frozen=True)
class CalibrationReport:
    n_rows: int
    n_evaluable: int
    n_hold_excluded: int
    n_missing_fields: int        # no entry price or no horizon
    n_too_young: int             # horizon not yet passed
    n_no_price: int              # lookup failed / returned nothing usable
    buckets: list[ConfidenceBucket] = field(default_factory=list)
    weighted_gap: float | None = None
    payoff: dict = field(default_factory=dict)
    override: dict = field(default_factory=dict)
    min_per_bucket: int = MIN_PER_BUCKET
    note: str = ""
    asof: str = ""


def _evaluate(rows: Sequence, price_lookup, now: datetime):
    """Split rows into evaluable (with direction, hit, latest) + counters."""
    counters = {"hold": 0, "missing": 0, "young": 0, "no_price": 0}
    evaluable: list[tuple[object, int, float, bool]] = []  # (row, dir, latest, hit)
    for r in rows:
        direction = DIRECTION.get(r.verdict)
        if direction is None:
            counters["hold"] += 1
            continue
        if r.entry_price is None or r.entry_price <= 0 or r.horizon_days is None:
            counters["missing"] += 1
            continue
        ts = r.ts if r.ts.tzinfo else r.ts.replace(tzinfo=timezone.utc)
        if now < ts + timedelta(days=r.horizon_days):
            counters["young"] += 1
            continue
        latest = price_lookup(r.symbol) if price_lookup is not None else None
        if latest is None or latest <= 0:
            counters["no_price"] += 1
            continue
        hit = (latest / r.entry_price - 1.0) * direction > 0
        evaluable.append((r, direction, latest, hit))
    return evaluable, counters


def _confidence_buckets(evaluable) -> tuple[list[ConfidenceBucket], float | None]:
    buckets: list[ConfidenceBucket] = []
    weighted_num = weighted_den = 0.0
    for lo, hi, label in BUCKET_EDGES:
        members = [(r, hit) for (r, _d, _l, hit) in evaluable
                   if lo <= r.confidence < hi]
        n = len(members)
        hits = sum(1 for _r, hit in members if hit)
        avg_conf = (sum(r.confidence for r, _h in members) / n) if n else None
        qualified = n >= MIN_PER_BUCKET
        hit_rate = (hits / n) if qualified else None
        gap = (hit_rate - avg_conf) \
            if (hit_rate is not None and avg_conf is not None) else None
        if qualified and gap is not None:
            weighted_num += n * gap
            weighted_den += n
        buckets.append(ConfidenceBucket(
            label=label, n=n, hits=hits, avg_stated_confidence=avg_conf,
            hit_rate=hit_rate, gap=gap, qualified=qualified))
    return buckets, (weighted_num / weighted_den) if weighted_den else None


def _payoff_vs_plan(evaluable) -> dict:
    """Planned vs realized R against the SAME stop distance. Endpoint-only."""
    planned: list[float] = []
    realized: list[float] = []
    n_with_plan = n_invalid = 0
    for r, direction, latest, _hit in evaluable:
        if r.target_price is None or r.stop_price is None:
            continue
        n_with_plan += 1
        risk = (r.entry_price - r.stop_price) * direction
        reward = (r.target_price - r.entry_price) * direction
        if risk <= 0 or reward <= 0:
            n_invalid += 1        # stop/target on the wrong side of entry
            continue
        planned.append(reward / risk)
        realized.append((latest - r.entry_price) * direction / risk)
    n_valid = len(planned)
    return {
        "n_with_plan": n_with_plan,
        "n_valid_geometry": n_valid,
        "n_invalid_geometry": n_invalid,
        "avg_planned_r": (sum(planned) / n_valid) if n_valid else None,
        "avg_realized_r": (sum(realized) / n_valid) if n_valid else None,
        "note": ("R measured against the stated stop distance; ENDPOINT-ONLY "
                 "(the journal has no price path — MAE/MFE live on T089). "
                 "Invalid geometry = stop or target on the wrong side of "
                 "entry, counted, never scored."),
    }


def _override_outcomes(rows: Sequence, evaluable) -> dict:
    marked = [r for r in rows if r.followed is not None]
    overridden_all = sum(1 for r in marked if r.followed is False)
    groups: dict[str, dict] = {}
    for name, want in (("followed", True), ("overridden", False)):
        members = [hit for (r, _d, _l, hit) in evaluable if r.followed is want]
        n = len(members)
        groups[name] = {
            "n": n,
            "hits": sum(1 for h in members if h),
            "hit_rate": (sum(1 for h in members if h) / n)
                        if n >= MIN_PER_BUCKET else None,
        }
    return {
        "marked": len(marked),
        "override_rate": (overridden_all / len(marked)) if marked else None,
        **groups,
        "note": ("hit rates only over AGED, marked decisions; groups under "
                 f"{MIN_PER_BUCKET} list their n and refuse a rate. A strong "
                 "overridden hit rate is coaching evidence (T067b), stated "
                 "as measurement — any strategy-weight change stays a "
                 "proposal the owner ratifies."),
    }


def compute_calibration(
    rows: Sequence,
    price_lookup: Callable[[str], float | None] | None = None,
    now: datetime | None = None,
) -> CalibrationReport:
    """The v2 report. Never raises on thin data — it counts what it could
    not judge and says so; an empty journal yields an all-None report."""
    now = now or datetime.now(timezone.utc)
    evaluable, c = _evaluate(rows, price_lookup, now)
    buckets, weighted_gap = _confidence_buckets(evaluable)
    return CalibrationReport(
        n_rows=len(rows),
        n_evaluable=len(evaluable),
        n_hold_excluded=c["hold"],
        n_missing_fields=c["missing"],
        n_too_young=c["young"],
        n_no_price=c["no_price"],
        buckets=buckets,
        weighted_gap=weighted_gap,
        payoff=_payoff_vs_plan(evaluable),
        override=_override_outcomes(rows, evaluable),
        note=("Calibration v2: positive gap = underconfident, negative = "
              "overconfident, judged ONLY on aged decisions with prices; "
              f"buckets under {MIN_PER_BUCKET} refuse a rate. Process "
              "measurement, not a performance promise."),
        asof=now.isoformat(),
    )
