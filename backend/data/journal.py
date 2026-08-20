"""Decision journal data layer (T063) — record, mark, summarize, calibrate.

The write path is called by the `record_decision` TOOL (the model records its own
recommendations — the persona requires it); the owner's follow/override arrives
via `mark_decision`. Outcome evaluation compares aged decisions against a caller-
supplied price lookup so the analysis stays pure and testable.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from data.models import DecisionJournal

VERDICTS = ("buy", "add", "hold", "trim", "sell", "avoid")
_DIRECTION = {"buy": 1, "add": 1, "trim": -1, "sell": -1, "avoid": -1}  # hold: no direction
DIRECTION = _DIRECTION  # public alias — calibration v2 (T063b) reads the same map


def record_decision(db: Session, **fields) -> DecisionJournal:
    if fields.get("verdict") not in VERDICTS:
        raise ValueError(f"verdict must be one of {VERDICTS}, got {fields.get('verdict')!r}")
    if not 0 <= fields.get("confidence", -1) <= 1:
        raise ValueError("confidence must be in [0, 1]")
    row = DecisionJournal(**fields)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def mark_decision(db: Session, decision_id: int, followed: bool,
                  note: str | None = None) -> DecisionJournal:
    row = db.get(DecisionJournal, decision_id)
    if row is None:
        raise ValueError(f"no journal entry with id {decision_id}")
    row.followed = followed
    row.follow_note = note
    db.commit()
    db.refresh(row)
    return row


def list_decisions(db: Session, limit: int = 20) -> list[DecisionJournal]:
    if not 1 <= limit <= 200:
        raise ValueError(f"limit must be 1..200, got {limit}")
    rows = db.execute(
        select(DecisionJournal).order_by(DecisionJournal.ts.desc()).limit(limit)
    ).scalars().all()
    return list(rows)


@dataclass(frozen=True)
class JournalSummary:
    total: int
    by_verdict: dict[str, int]
    avg_confidence: float | None
    followed: int
    overridden: int
    unmarked: int
    evaluated: int          # aged decisions with entry price + direction + a price
    hits: int               # realized move agreed with the verdict's direction
    hit_rate: float | None  # hits / evaluated; None when nothing evaluable yet
    note: str


def summarize_decisions(
    rows: Sequence[DecisionJournal],
    price_lookup: Callable[[str], float | None] | None = None,
    now: datetime | None = None,
) -> JournalSummary:
    """Deterministic summary + v1 calibration: a decision is EVALUABLE once its
    horizon has passed and it has an entry price and a direction (hold is
    direction-less and excluded). Hit = sign(latest - entry) matches the verdict.
    price_lookup returns the latest price for a symbol, or None if unavailable."""
    now = now or datetime.now(timezone.utc)
    by_verdict: dict[str, int] = {}
    for r in rows:
        by_verdict[r.verdict] = by_verdict.get(r.verdict, 0) + 1
    confidences = [r.confidence for r in rows]

    evaluated = hits = 0
    if price_lookup is not None:
        for r in rows:
            direction = _DIRECTION.get(r.verdict)
            if direction is None or r.entry_price is None or r.horizon_days is None:
                continue
            ts = r.ts if r.ts.tzinfo else r.ts.replace(tzinfo=timezone.utc)
            if now < ts + timedelta(days=r.horizon_days):
                continue  # too young to judge
            latest = price_lookup(r.symbol)
            if latest is None or latest <= 0 or r.entry_price <= 0:
                continue
            evaluated += 1
            realized = latest / r.entry_price - 1.0
            if realized * direction > 0:
                hits += 1

    return JournalSummary(
        total=len(rows),
        by_verdict=by_verdict,
        avg_confidence=(sum(confidences) / len(confidences)) if confidences else None,
        followed=sum(1 for r in rows if r.followed is True),
        overridden=sum(1 for r in rows if r.followed is False),
        unmarked=sum(1 for r in rows if r.followed is None),
        evaluated=evaluated,
        hits=hits,
        hit_rate=(hits / evaluated) if evaluated else None,
        note=(
            "Calibration v1: direction-only hits after the stated horizon, judged "
            "against the latest price. Hold verdicts and unaged entries are "
            "excluded. Hit rate is a process check, not a performance claim."
        ),
    )


def decision_as_dict(r: DecisionJournal) -> dict:
    return {
        "id": r.id,
        "ts": r.ts.isoformat(),
        "symbol": r.symbol,
        "verdict": r.verdict,
        "confidence": r.confidence,
        "thesis": r.thesis,
        "horizon_days": r.horizon_days,
        "entry_price": r.entry_price,
        "target_price": r.target_price,
        "stop_price": r.stop_price,
        "key_risk": r.key_risk,
        "regime": r.regime,
        "regime_confidence": r.regime_confidence,
        "followed": r.followed,
        "follow_note": r.follow_note,
        "conversation_id": r.conversation_id,
        "source": r.source,
    }
