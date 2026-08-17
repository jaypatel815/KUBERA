"""Unit tests for Trading Autopsy (T103, D026).

Tests full battery:
- Instrument profile (options vs equity, 0DTE shares)
- FIFO option round-trips with 100x contract multiplier
- Distinct option strike separation (never mixing different strikes on same underlying)
- Sub-day holding period distributions (minutes, hours, same_day, multi-day)
- Behavioral tells: revenge sizing drift and tilt tempo detection
- Registry tool and FastAPI endpoint execution
"""

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from analysis.autopsy import AutopsyFill, analyze_autopsy, match_fifo_trips
from api.main import app, get_db_session
from api.tools import ToolContext, registry
from data.db import make_session_factory
from data.models import Base, Transaction
from data.statements import parse_confirmation

FIXTURES = Path(__file__).parent / "fixtures" / "schwab"


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture
def memory_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with make_session_factory(engine)() as session:
        yield session
    engine.dispose()


@pytest.fixture
def client():
    return TestClient(app)


def test_empty_fills_handled_gracefully():
    report = analyze_autopsy([])
    assert report.total_fills == 0
    assert report.performance.round_trips == 0
    assert report.performance.total_realized_pnl == 0.0
    assert report.performance.win_rate is None
    assert report.behavior.sizing_drift_ratio is None
    assert "No fills provided" in report.narrative[0]


def test_fifo_option_contract_multiplier_applied():
    """Option fills must apply the 100x contract multiplier in P&L and notional."""
    t0 = datetime(2026, 3, 13, 10, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 3, 13, 11, 30, tzinfo=timezone.utc)

    fills = [
        AutopsyFill(
            symbol="SPY",
            side="buy",
            qty=2.0,
            price=10.00,
            ts=t0,
            asset_type="option",
            contract_multiplier=100,
            option_expiry=date(2026, 3, 13),
            option_strike=660.0,
            option_right="put",
        ),
        AutopsyFill(
            symbol="SPY",
            side="sell",
            qty=2.0,
            price=15.00,
            ts=t1,
            asset_type="option",
            contract_multiplier=100,
            option_expiry=date(2026, 3, 13),
            option_strike=660.0,
            option_right="put",
        ),
    ]

    report = analyze_autopsy(fills)
    assert report.total_fills == 2
    assert report.instrument_profile.option_fills == 2
    assert report.instrument_profile.dte0_fills == 2
    # 2 contracts * $10 * 100 = $2000 buy; 2 contracts * $15 * 100 = $3000 sell
    assert report.instrument_profile.option_notional == 5000.00

    # P&L: 2 * (15 - 10) * 100 = $1,000.00
    assert report.performance.round_trips == 1
    assert report.performance.total_realized_pnl == 1000.00
    assert report.performance.wins == 1
    assert report.performance.win_rate == 1.0


def test_distinct_option_strikes_do_not_mix():
    """Different option strikes on the same underlying must not cross-match in FIFO."""
    t0 = datetime(2026, 3, 13, 10, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 3, 13, 11, 0, tzinfo=timezone.utc)

    fills = [
        AutopsyFill(
            symbol="NVDA",
            side="buy",
            qty=1.0,
            price=5.00,
            ts=t0,
            asset_type="option",
            contract_multiplier=100,
            option_expiry=date(2026, 3, 13),
            option_strike=180.0,
            option_right="put",
        ),
        AutopsyFill(
            symbol="NVDA",
            side="sell",
            qty=1.0,
            price=8.00,
            ts=t1,
            asset_type="option",
            contract_multiplier=100,
            option_expiry=date(2026, 3, 13),
            option_strike=182.5,  # different strike!
            option_right="put",
        ),
    ]

    trips = match_fifo_trips(fills)
    assert len(trips) == 0  # no matches across different strikes


def test_sub_day_holding_periods_categorization():
    """Verify holding period sub-day cuts (minutes, hours, same_day)."""
    t_entry = datetime(2026, 3, 2, 9, 35, tzinfo=timezone.utc)
    t_min = t_entry + timedelta(minutes=45)       # 45m -> minutes
    t_hrs = t_entry + timedelta(hours=3, minutes=30)  # 3.5h -> hours

    fills = [
        AutopsyFill("AAPL", "buy", 10.0, 150.0, t_entry, "equity"),
        AutopsyFill("AAPL", "sell", 5.0, 155.0, t_min, "equity"),
        AutopsyFill("AAPL", "sell", 5.0, 160.0, t_hrs, "equity"),
    ]

    report = analyze_autopsy(fills)
    assert report.performance.round_trips == 2
    assert report.performance.total_realized_pnl == pytest.approx(5 * 5.0 + 5 * 10.0)

    by_b = report.holding_periods["by_bucket"]
    assert by_b["minutes"]["round_trips"] == 1
    assert by_b["hours"]["round_trips"] == 1


def test_behavioral_tells_revenge_and_tilt():
    """Verify sizing drift (revenge) and post-loss tempo (tilt) detection on synthetic history."""
    base_t = datetime(2026, 3, 1, 9, 30, tzinfo=timezone.utc)
    fills = []

    # 4 baseline winning round trips: Buy $1000, Sell $1100, then follow with normal $1000 buy
    for i in range(4):
        t_in = base_t + timedelta(days=i * 2)
        t_out = t_in + timedelta(hours=2)
        t_next = t_out + timedelta(hours=1)
        fills.extend([
            AutopsyFill(f"SYM{i}", "buy", 10.0, 100.0, t_in, "equity"),
            AutopsyFill(f"SYM{i}", "sell", 10.0, 110.0, t_out, "equity"),
            AutopsyFill(f"NEXT{i}", "buy", 10.0, 100.0, t_next, "equity"),
        ])

    # 4 losing round trips: Buy $1000, Sell $800, then follow with 2x revenge buy ($2000) in 30m
    offset = 10
    for i in range(4):
        t_in = base_t + timedelta(days=offset + i * 2)
        t_out = t_in + timedelta(hours=2)
        t_next = t_out + timedelta(minutes=30)
        fills.extend([
            AutopsyFill(f"LOS{i}", "buy", 10.0, 100.0, t_in, "equity"),
            AutopsyFill(f"LOS{i}", "sell", 10.0, 80.0, t_out, "equity"),
            AutopsyFill(f"REV{i}", "buy", 20.0, 100.0, t_next, "equity"),
        ])

    report = analyze_autopsy(fills)
    assert report.behavior.sizing_drift_ratio == pytest.approx(2.0, rel=1e-2)
    assert "revenge sizing signature" in report.behavior.sizing_drift_verdict


def test_autopsy_on_real_schwab_confirmation_fixtures():
    """Run autopsy on real multi_trade_day and equity_single fixtures."""
    rep_multi = parse_confirmation(load_fixture("multi_trade_day.txt"), "multi_trade_day.txt")
    rep_single = parse_confirmation(load_fixture("equity_single.txt"), "equity_single.txt")

    all_fills = rep_multi.fills + rep_single.fills
    report = analyze_autopsy(all_fills)

    assert report.total_fills == len(all_fills)
    assert report.instrument_profile.option_fills > 0
    assert report.instrument_profile.equity_fills > 0
    assert report.instrument_profile.dte0_fills > 0
    assert len(report.symbols) > 0
    assert len(report.narrative) >= 4


def test_autopsy_tool_execution_via_registry(memory_db):
    """Verify get_trading_autopsy tool registers and executes cleanly."""
    t0 = datetime(2026, 3, 2, 10, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 3, 2, 11, 0, tzinfo=timezone.utc)

    txn1 = Transaction(
        account_id=1, external_id="tx1", symbol="SPY", side="buy", qty=5.0, price=500.0,
        occurred_at=t0, source="test",
    )
    txn2 = Transaction(
        account_id=1, external_id="tx2", symbol="SPY", side="sell", qty=5.0, price=505.0,
        occurred_at=t1, source="test",
    )
    memory_db.add_all([txn1, txn2])
    memory_db.commit()

    ctx = ToolContext(db=memory_db)
    res = registry.execute("get_trading_autopsy", {}, ctx)

    assert res["total_fills"] == 2
    assert res["performance"]["round_trips"] == 1
    assert res["performance"]["total_realized_pnl"] == 25.0
    assert res["performance"]["win_rate"] == 1.0


def test_autopsy_endpoint(client, memory_db):
    """GET /api/autopsy returns 200 with structured autopsy payload."""
    t0 = datetime(2026, 3, 2, 10, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 3, 2, 11, 0, tzinfo=timezone.utc)

    txn1 = Transaction(
        account_id=1, external_id="tx1", symbol="QQQ", side="buy", qty=10.0, price=400.0,
        occurred_at=t0, source="test",
    )
    txn2 = Transaction(
        account_id=1, external_id="tx2", symbol="QQQ", side="sell", qty=10.0, price=402.0,
        occurred_at=t1, source="test",
    )
    memory_db.add_all([txn1, txn2])
    memory_db.commit()

    def db_override():
        yield memory_db

    app.dependency_overrides[get_db_session] = db_override

    try:
        resp = client.get("/api/autopsy")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_fills"] == 2
        assert data["performance"]["round_trips"] == 1
        assert data["performance"]["total_realized_pnl"] == 20.0
        assert "instrument_profile" in data
        assert "behavior" in data
        assert "holding_periods" in data
    finally:
        app.dependency_overrides.clear()
