"""Risk-state persistence (T035): the breaker must survive restarts (spec §8).

One logical row (id=1). The paper loop restores before acting and persists after every
equity mark, so the database always reflects the latest engine state.
"""

import json

from sqlalchemy.orm import Session

from data.models import RiskState, utcnow
from risk.engine import RiskEngine

RISK_STATE_ID = 1


def restore_risk_state(session: Session, engine: RiskEngine) -> bool:
    """Rehydrate the engine from the DB. Returns True if saved state existed."""
    row = session.get(RiskState, RISK_STATE_ID)
    if row is None:
        return False
    engine.restore(
        day=row.day,
        day_start_equity=row.day_start_equity,
        tripped=row.tripped,
        trip_reason=row.trip_reason,
        lockout_until=row.lockout_until,
        buys_day=row.buys_day,
        buys_today=row.buys_today or 0,
    )
    try:  # T065: disabled symbols ride the same row; a corrupt list is empty, loudly
        engine.set_disabled_symbols(json.loads(row.disabled_symbols_json or "[]"))
    except (ValueError, TypeError):
        engine.set_disabled_symbols([])
    return True


def persist_risk_state(session: Session, engine: RiskEngine) -> None:
    row = session.get(RiskState, RISK_STATE_ID)
    if row is None:
        row = RiskState(id=RISK_STATE_ID)
        session.add(row)
    row.day = engine.day
    row.day_start_equity = engine.day_start_equity
    row.tripped = engine.tripped
    row.trip_reason = engine.trip_reason
    row.lockout_until = engine.lockout_until
    row.disabled_symbols_json = json.dumps(sorted(engine.disabled_symbols))
    row.buys_day, row.buys_today = engine.buys_state
    row.updated_at = utcnow()
    session.commit()
