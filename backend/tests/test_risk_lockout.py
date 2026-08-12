"""The commitment device (owner request 2026-08-12): after a trip, reset() is refused
until the cooling-off period passes — no override parameter exists, deliberately."""

from datetime import datetime, timedelta, timezone

import pytest

from data.db import make_engine, make_session_factory
from data.models import Base
from risk.engine import LockoutActiveError, RiskEngine, RiskLimits
from risk.persistence import persist_risk_state, restore_risk_state

TRIP_TIME = datetime(2026, 8, 12, 15, 0, 0, tzinfo=timezone.utc)


def tripped_engine(cooldown_hours=20.0) -> RiskEngine:
    e = RiskEngine(limits=RiskLimits(cooldown_hours=cooldown_hours))
    e.start_day(equity=100_000.0, day="2026-08-12")
    e.record_equity(96_000.0, TRIP_TIME)  # -4% -> trip
    assert e.tripped
    return e


def test_trip_sets_lockout_from_cooldown():
    e = tripped_engine(cooldown_hours=20.0)
    assert e.lockout_until == TRIP_TIME + timedelta(hours=20)


def test_reset_refused_during_cooldown_with_remaining_time():
    e = tripped_engine()
    with pytest.raises(LockoutActiveError) as exc:
        e.reset("I promise I'm calm now", now=TRIP_TIME + timedelta(hours=1))
    assert "19.0h" in str(exc.value)
    assert e.tripped  # nothing changed


def test_reset_refused_even_one_minute_before_expiry():
    e = tripped_engine()
    with pytest.raises(LockoutActiveError):
        e.reset("so close", now=TRIP_TIME + timedelta(hours=19, minutes=59))


def test_reset_allowed_after_cooldown():
    e = tripped_engine()
    e.reset("reviewed the drawdown next morning", now=TRIP_TIME + timedelta(hours=20, minutes=1))
    assert not e.tripped
    assert e.lockout_until is None


def test_zero_cooldown_preserves_legacy_behavior():
    e = tripped_engine(cooldown_hours=0)
    e.reset("immediate reset allowed when cooldown configured to 0", now=TRIP_TIME)
    assert not e.tripped


def test_lockout_survives_restart():
    """Restart during the cooldown must not shorten it — persistence includes lockout."""
    engine_db = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine_db)
    with make_session_factory(engine_db)() as db:
        e1 = tripped_engine()
        persist_risk_state(db, e1)

        e2 = RiskEngine(limits=RiskLimits(cooldown_hours=20.0))  # "restart"
        restore_risk_state(db, e2)
        assert e2.tripped
        assert e2.lockout_until == e1.lockout_until
        with pytest.raises(LockoutActiveError):
            e2.reset("restart won't save you", now=TRIP_TIME + timedelta(hours=2))
    engine_db.dispose()


def test_cooldown_validation():
    with pytest.raises(ValueError):
        RiskLimits(cooldown_hours=-1)
    with pytest.raises(ValueError):
        RiskLimits(cooldown_hours=1000)
