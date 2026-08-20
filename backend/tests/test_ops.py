"""Ops scripts (D018): backup_db retention + health_check logic — pure functions
tested with fakes; the Windows toast side effect is deliberately not under test."""

import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from sqlalchemy.orm import Session

from data.db import make_engine
from data.models import AccountSnapshot, Base, BrokerAccount, RiskState

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"


def load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


backup_db = load_script("backup_db")
health_check = load_script("health_check")


# --- backup_db ----------------------------------------------------------------

def test_backup_creates_timestamped_copy_and_prunes(tmp_path):
    db = tmp_path / "kubera.sqlite3"
    db.write_bytes(b"data-v1")
    dest_dir = tmp_path / "backups"

    first, pruned = backup_db.backup_database(
        db, dest_dir, keep=2, now=datetime(2026, 8, 13, 23, 30, 0))
    assert first.name == "kubera-20260813-233000.sqlite3"
    assert first.read_bytes() == b"data-v1" and pruned == []

    db.write_bytes(b"data-v2")
    second, _ = backup_db.backup_database(
        db, dest_dir, keep=2, now=datetime(2026, 8, 14, 23, 30, 0))
    third, pruned = backup_db.backup_database(
        db, dest_dir, keep=2, now=datetime(2026, 8, 15, 23, 30, 0))
    # keep=2 -> the oldest of the three is pruned, newest two remain
    assert [p.name for p in pruned] == ["kubera-20260813-233000.sqlite3"]
    assert sorted(p.name for p in dest_dir.glob("*.sqlite3")) == [
        "kubera-20260814-233000.sqlite3", "kubera-20260815-233000.sqlite3",
    ]
    assert third.read_bytes() == b"data-v2"


def test_backup_fails_closed(tmp_path):
    with pytest.raises(FileNotFoundError, match="database not found"):
        backup_db.backup_database(tmp_path / "missing.sqlite3", tmp_path / "b", keep=3)
    (tmp_path / "kubera.sqlite3").write_bytes(b"x")
    with pytest.raises(ValueError, match="keep"):
        backup_db.backup_database(tmp_path / "kubera.sqlite3", tmp_path / "b", keep=0)


# --- health_check -------------------------------------------------------------

@pytest.fixture()
def db():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
    engine.dispose()


def test_check_server_ok_and_down():
    ok = httpx.Client(transport=httpx.MockTransport(
        lambda req: httpx.Response(200, json={"status": "ok"})))
    assert health_check.check_server("http://test", client=ok) == []

    def boom(request):
        raise httpx.ConnectError("refused")

    down = httpx.Client(transport=httpx.MockTransport(boom))
    problems = health_check.check_server("http://test", client=down)
    assert len(problems) == 1 and "unreachable" in problems[0]


def test_check_breaker(db):
    assert health_check.check_breaker(db) == []  # no state row yet -> quiet
    db.add(RiskState(id=1, tripped=True, trip_reason="daily loss 3.2%"))
    db.commit()
    problems = health_check.check_breaker(db)
    assert len(problems) == 1
    assert "TRIPPED" in problems[0] and "3.2%" in problems[0]


def test_check_sync_freshness(db):
    problems = health_check.check_sync_freshness(db, max_age_minutes=30)
    assert problems and "sync.py" in problems[0]  # never synced -> actionable message

    acct = BrokerAccount(broker="alpaca-paper", external_id="A1")
    db.add(acct)
    db.flush()
    now = datetime(2026, 8, 13, 15, 0, 0, tzinfo=timezone.utc)
    db.add(AccountSnapshot(
        account_id=acct.id, equity=1.0, cash=1.0, buying_power=1.0,
        asof=now - timedelta(minutes=5), source="alpaca-paper"))
    db.commit()
    assert health_check.check_sync_freshness(db, 30, now=now) == []  # 5 min old: fine

    problems = health_check.check_sync_freshness(db, 30, now=now + timedelta(hours=1))
    assert len(problems) == 1 and "65 min old" in problems[0]


def _acct_client(equity: float | None, status: int = 200) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if equity is None:
            raise httpx.ConnectError("refused")
        return httpx.Response(status, json={"equity": equity, "cash": 1.0})
    return httpx.Client(transport=httpx.MockTransport(handler))


def _snapshot(db, equity: float):
    acct = BrokerAccount(broker="alpaca-paper", external_id="A2")
    db.add(acct)
    db.flush()
    now = datetime(2026, 8, 14, 15, 0, 0, tzinfo=timezone.utc)
    db.add(AccountSnapshot(account_id=acct.id, equity=equity, cash=1.0,
                           buying_power=1.0, asof=now, source="alpaca-paper"))
    db.commit()
    return now


def test_reconciliation_flags_drift(db):
    # snapshot 100,000 vs broker 101,000 -> 0.99% drift > 0.5% threshold
    now = _snapshot(db, 100_000.0)
    problems = health_check.check_reconciliation(
        "http://test", db, client=_acct_client(101_000.0), now=now)
    assert len(problems) == 1
    assert "RECONCILIATION" in problems[0]
    assert "0.99%" in problems[0]
    assert "sync.py" in problems[0]  # the remedy is named


def test_reconciliation_quiet_within_threshold(db):
    # 100,000 vs 100,200 -> 0.2% drift: fine
    now = _snapshot(db, 100_000.0)
    assert health_check.check_reconciliation(
        "http://test", db, client=_acct_client(100_200.0), now=now) == []


def test_reconciliation_quiet_when_it_cannot_judge(db):
    # no snapshot: freshness check owns that story
    assert health_check.check_reconciliation(
        "http://test", db, client=_acct_client(100_000.0)) == []
    # server down: check_server owns that story
    _snapshot(db, 100_000.0)
    assert health_check.check_reconciliation(
        "http://test", db, client=_acct_client(None)) == []
    # bad payload (equity 0): refuse to divide, stay quiet
    assert health_check.check_reconciliation(
        "http://test", db, client=_acct_client(0.0)) == []


# --- check_feed (T129 - Phase 8 "data feed outages") --------------------------

from types import SimpleNamespace  # noqa: E402


def _feed_settings(configured=True):
    return SimpleNamespace(alpaca_configured=configured)


def _trade(age_seconds: float, now: datetime):
    ts = now - timedelta(seconds=age_seconds)
    return SimpleNamespace(exchange_ts=ts, age_human=f"{age_seconds:.0f}s")


class _Market:
    def __init__(self, trade=None, exc=None):
        self.trade, self.exc = trade, exc

    def get_latest_trade(self, symbol):
        if self.exc:
            raise self.exc
        return self.trade

    def close(self):
        pass


class _Clock:
    def __init__(self, is_open):
        self._open = is_open

    def get_clock(self):
        return SimpleNamespace(is_open=self._open)


def test_check_feed_quiet_when_unconfigured():
    # an unconfigured box is not an outage
    assert health_check.check_feed(settings=_feed_settings(False)) == []


def test_check_feed_names_unreachable_feed():
    problems = health_check.check_feed(
        settings=_feed_settings(),
        market=_Market(exc=httpx.ConnectError("boom")))
    assert len(problems) == 1
    assert "FEED unreachable" in problems[0]
    assert "ConnectError" in problems[0]


def test_check_feed_quiet_on_fresh_print_while_open():
    now = datetime.now(timezone.utc)
    problems = health_check.check_feed(
        settings=_feed_settings(), market=_Market(trade=_trade(30, now)),
        alpaca=_Clock(is_open=True), now=now)
    assert problems == []


def test_check_feed_flags_stale_print_while_open():
    # market OPEN but the print is 20 minutes old = the feed is behind
    now = datetime.now(timezone.utc)
    problems = health_check.check_feed(
        settings=_feed_settings(), market=_Market(trade=_trade(1200, now)),
        alpaca=_Clock(is_open=True), now=now)
    assert len(problems) == 1 and "FEED STALE" in problems[0]
    assert "feed is behind" in problems[0]


def test_check_feed_wallclock_fallback_without_broker_clock():
    # no clock: T036b's fallback deliberately assumes OPEN (conservative),
    # so a 5-day-old print flags STALE — and admits the state is unknown
    now = datetime.now(timezone.utc)
    problems = health_check.check_feed(
        settings=_feed_settings(),
        market=_Market(trade=_trade(5 * 24 * 3600, now)), now=now)
    assert len(problems) == 1 and "FEED STALE" in problems[0]
    assert "market state unknown" in problems[0]
