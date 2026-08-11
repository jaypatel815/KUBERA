"""equity_history: last snapshot per day per account, summed across accounts."""

from datetime import datetime, timezone

import pytest

from data.db import make_engine, make_session_factory
from data.history import equity_history
from data.models import AccountSnapshot, Base, BrokerAccount


@pytest.fixture()
def session():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with make_session_factory(engine)() as s:
        yield s
    engine.dispose()


def ts(day: int, hour: int) -> datetime:
    return datetime(2026, 8, day, hour, 0, 0, tzinfo=timezone.utc)


def snap(account_id: int, equity: float, asof: datetime) -> AccountSnapshot:
    return AccountSnapshot(
        account_id=account_id, equity=equity, cash=0.0, buying_power=0.0,
        asof=asof, source="alpaca-paper",
    )


def test_last_snapshot_per_day_wins_and_accounts_sum(session):
    a1 = BrokerAccount(broker="alpaca-paper", external_id="A1")
    a2 = BrokerAccount(broker="alpaca-paper", external_id="A2")
    session.add_all([a1, a2])
    session.flush()
    session.add_all([
        snap(a1.id, 100.0, ts(1, 9)),   # superseded same day
        snap(a1.id, 105.0, ts(1, 16)),  # last of day 1 for a1
        snap(a2.id, 50.0, ts(1, 15)),   # a2 day 1
        snap(a1.id, 110.0, ts(2, 16)),  # day 2, a1 only
    ])
    session.commit()

    points = equity_history(session)
    assert points == [("2026-08-01", 155.0), ("2026-08-02", 110.0)]


def test_days_window_limits_output(session):
    a1 = BrokerAccount(broker="alpaca-paper", external_id="A1")
    session.add(a1)
    session.flush()
    for day in (1, 2, 3):
        session.add(snap(a1.id, 100.0 + day, ts(day, 16)))
    session.commit()
    assert [d for d, _ in equity_history(session, days=2)] == ["2026-08-02", "2026-08-03"]


def test_days_validation(session):
    with pytest.raises(ValueError):
        equity_history(session, days=0)
