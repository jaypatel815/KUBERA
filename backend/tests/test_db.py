"""Schema v1 tests: CRUD roundtrip, constraints, UTC enforcement, and — most importantly —
migration parity: `alembic upgrade head` must produce the same tables the models define."""

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import inspect, select

from data.db import make_engine, make_session_factory
from data.models import AccountSnapshot, Base, BrokerAccount, PositionSnapshot, Transaction

REPO_ROOT = Path(__file__).resolve().parents[2]

NOW = datetime.now(timezone.utc)


@pytest.fixture()
def session():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = make_session_factory(engine)
    with factory() as s:
        yield s
    engine.dispose()


def _account(s):
    acct = BrokerAccount(broker="alpaca-paper", external_id="TEST123", currency="USD")
    s.add(acct)
    s.commit()
    return acct


def test_snapshot_roundtrip_preserves_utc(session):
    acct = _account(session)
    session.add(
        AccountSnapshot(
            account_id=acct.id, equity=100000.75, cash=25000.5, buying_power=200001.5,
            asof=NOW, source="alpaca-paper",
        )
    )
    session.add(
        PositionSnapshot(
            account_id=acct.id, symbol="AAPL", qty=10, avg_entry_price=150.25,
            current_price=165.10, market_value=1651.0, cost_basis=1502.5,
            unrealized_pl=148.5, asof=NOW, source="alpaca-paper",
        )
    )
    session.commit()
    snap = session.execute(select(AccountSnapshot)).scalar_one()
    pos = session.execute(select(PositionSnapshot)).scalar_one()
    assert snap.asof.tzinfo is not None and snap.asof == NOW
    assert pos.asof.tzinfo is not None
    assert pos.market_value == pytest.approx(1651.0)


def test_naive_datetime_rejected(session):
    acct = _account(session)
    session.add(
        AccountSnapshot(
            account_id=acct.id, equity=1.0, cash=1.0, buying_power=1.0,
            asof=datetime(2026, 8, 11, 12, 0, 0),  # naive on purpose
            source="alpaca-paper",
        )
    )
    with pytest.raises(Exception) as exc:
        session.commit()
    assert "naive datetime rejected" in str(exc.value)


def test_duplicate_transaction_rejected(session):
    acct = _account(session)
    txn = dict(
        account_id=acct.id, external_id="FILL-1", symbol="SPY", side="buy",
        qty=5, price=558.10, occurred_at=NOW, source="alpaca-paper",
    )
    session.add(Transaction(**txn))
    session.commit()
    session.add(Transaction(**txn))
    with pytest.raises(Exception):
        session.commit()


def test_alembic_migration_matches_models(tmp_path):
    """upgrade head on a fresh DB must create every table the models define."""
    db_path = tmp_path / "migrate_test.sqlite3"
    env = {"DATABASE_URL": f"sqlite:///{db_path.as_posix()}", "PATH": "/usr/bin:/bin"}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "backend/alembic.ini", "upgrade", "head"],
        cwd=REPO_ROOT, env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, f"alembic failed:\n{result.stderr[-800:]}"
    engine = make_engine(f"sqlite:///{db_path.as_posix()}")
    tables = set(inspect(engine).get_table_names())
    engine.dispose()
    assert set(Base.metadata.tables) <= tables, f"missing: {set(Base.metadata.tables) - tables}"
