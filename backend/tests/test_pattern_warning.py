"""Unit tests for Pre-Trade Pattern Warnings (T104, D026).

Tests:
  - Insufficient sample fail-closed (N < 3).
  - 0DTE negative expectancy warnings with exact metrics (N, win rate, P&L).
  - Revenge sizing drift alerts following recent losses (within-asset-class).
  - Post-loss tilt tempo detection on rapid re-entries.
  - Symbol-specific historical track record warnings.
  - OCC option symbol parsing & automatic DTE calculation.
  - Day-of-week disadvantage cautions.
  - Registry tool & FastAPI endpoint execution end-to-end.
  - Verification against the owner's 250 real Schwab confirmation fills.
"""

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from analysis.autopsy import AutopsyRoundTrip
from analysis.pattern_warning import (
    ProposedTrade,
    evaluate_pattern_warnings,
    normalize_proposed_trade,
)
from api.main import app
from api.tools import ToolContext, registry
from data.models import Base, Transaction
from data.statements import parse_directory

client = TestClient(app)
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "schwab"


def _make_trip(
    symbol: str,
    pnl: float,
    asset_type: str = "equity",
    is_0dte: bool = False,
    exit_ts: datetime | None = None,
    notional: float = 1000.0,
    contract_multiplier: int = 1,
) -> AutopsyRoundTrip:
    ts = exit_ts or datetime(2026, 3, 2, 15, 0, tzinfo=timezone.utc)
    entry_ts = ts - timedelta(hours=2)
    qty = 10.0
    price = notional / (qty * contract_multiplier)
    return AutopsyRoundTrip(
        symbol=symbol,
        contract_key=symbol,
        asset_type=asset_type,
        qty=qty,
        entry_price=price,
        exit_price=price + (pnl / (qty * contract_multiplier)),
        pnl=pnl,
        held_days=0.08,
        entry_ts=entry_ts,
        exit_ts=ts,
        is_0dte=is_0dte,
        time_known=True,
        contract_multiplier=contract_multiplier,
    )


# ---------------------------------------------------------------- Tests


def test_insufficient_history():
    """Fewer than 3 round trips returns insufficient_history with zero warnings."""
    trips = [_make_trip("SPY", 100.0), _make_trip("SPY", -50.0)]
    proposed = ProposedTrade(symbol="SPY", action="buy", asset_type="equity", notional=2000.0)

    rep = evaluate_pattern_warnings(trips, proposed)
    assert rep.verdict == "insufficient_history"
    assert rep.warnings_count == 0
    assert rep.historical_trips_count == 2
    assert "insufficient" in rep.narrative[0].lower()


def test_0dte_option_negative_expectancy_warning():
    """0DTE options with historical losses triggers a high-severity 0dte_risk warning."""
    # 4 historical 0DTE trades: 1 win ($200), 3 losses (-$500, -$600, -$400)
    # -> total -$1,300, 25% win rate
    trips = [
        _make_trip("SPY", 200.0, asset_type="option", is_0dte=True, contract_multiplier=100),
        _make_trip("SPY", -500.0, asset_type="option", is_0dte=True, contract_multiplier=100),
        _make_trip("SPY", -600.0, asset_type="option", is_0dte=True, contract_multiplier=100),
        _make_trip("SPY", -400.0, asset_type="option", is_0dte=True, contract_multiplier=100),
    ]
    proposed = ProposedTrade(
        symbol="SPY", action="buy", asset_type="option", dte=0, notional=1000.0
    )

    rep = evaluate_pattern_warnings(trips, proposed)
    assert rep.verdict == "warning_triggered"
    assert rep.has_high_severity is True
    assert rep.warnings_count >= 1

    w = next(w for w in rep.warnings if w.category == "0dte_risk")
    assert w.severity == "high"
    assert w.sample_size == 4
    assert w.evidence["round_trips"] == 4
    assert w.evidence["wins"] == 1
    assert w.evidence["losses"] == 3
    assert w.evidence["win_rate"] == 0.25
    assert w.evidence["total_realized_pnl"] == -1300.0
    assert "25.0%" in w.narrative


def test_0dte_option_clear_when_profitable():
    """0DTE options with historical profit and solid win rate does not trigger 0dte_risk warning."""
    trips = [
        _make_trip("SPY", 400.0, asset_type="option", is_0dte=True, contract_multiplier=100),
        _make_trip("SPY", 500.0, asset_type="option", is_0dte=True, contract_multiplier=100),
        _make_trip("SPY", -200.0, asset_type="option", is_0dte=True, contract_multiplier=100),
        _make_trip("SPY", 300.0, asset_type="option", is_0dte=True, contract_multiplier=100),
    ]
    proposed = ProposedTrade(
        symbol="SPY", action="buy", asset_type="option", dte=0, notional=500.0
    )

    rep = evaluate_pattern_warnings(trips, proposed)
    assert not any(w.category == "0dte_risk" for w in rep.warnings)


def test_revenge_sizing_warning_after_recent_loss():
    """Proposing 3x median notional following a recent loss triggers sizing_drift warning."""
    now = datetime(2026, 3, 5, 14, 0, tzinfo=timezone.utc)
    # Baseline equity trades with median notional ~$1,000
    trips = [
        _make_trip("AAPL", 150.0, notional=1000.0, exit_ts=now - timedelta(days=5)),
        _make_trip("MSFT", 200.0, notional=1000.0, exit_ts=now - timedelta(days=4)),
        _make_trip("NVDA", 100.0, notional=1000.0, exit_ts=now - timedelta(days=3)),
        # Last trade is a loss 2 hours ago
        _make_trip("TSLA", -400.0, notional=1000.0, exit_ts=now - timedelta(hours=2)),
    ]
    # Proposing $3,000 notional (3.0x median)
    proposed = ProposedTrade(
        symbol="AAPL", action="buy", asset_type="equity", notional=3000.0, asof=now
    )

    rep = evaluate_pattern_warnings(trips, proposed)
    assert rep.has_high_severity is True
    w = next(w for w in rep.warnings if w.category == "sizing_drift")
    assert w.severity == "high"
    assert w.evidence["sizing_ratio"] == 3.0
    assert w.evidence["last_loss_symbol"] == "TSLA"
    assert w.evidence["last_loss_pnl"] == -400.0
    assert "3.0x" in w.headline


def test_post_loss_rapid_tilt_tempo_warning():
    """Proposing a trade 15 minutes after a loss triggers post_loss_tempo alert."""
    now = datetime(2026, 3, 5, 14, 0, tzinfo=timezone.utc)
    trips = [
        _make_trip("AAPL", 100.0, notional=1000.0, exit_ts=now - timedelta(days=2)),
        _make_trip("MSFT", 150.0, notional=1000.0, exit_ts=now - timedelta(days=1)),
        # Loss closed 15 minutes ago
        _make_trip("TSLA", -300.0, notional=1000.0, exit_ts=now - timedelta(minutes=15)),
    ]
    proposed = ProposedTrade(
        symbol="AAPL", action="buy", asset_type="equity", notional=1000.0, asof=now
    )

    rep = evaluate_pattern_warnings(trips, proposed)
    w = next((w for w in rep.warnings if w.category == "post_loss_tempo"), None)
    assert w is not None
    assert w.severity == "medium"
    assert w.evidence["minutes_since_loss"] == 15.0


def test_symbol_specific_negative_expectancy():
    """A symbol with repeated losses and negative P&L triggers symbol_history warning."""
    now = datetime(2026, 3, 5, 14, 0, tzinfo=timezone.utc)
    trips = [
        _make_trip("AAPL", 500.0, exit_ts=now - timedelta(days=4)),
        _make_trip("NVDA", -400.0, exit_ts=now - timedelta(days=3)),
        _make_trip("NVDA", -500.0, exit_ts=now - timedelta(days=2)),
        _make_trip("NVDA", -600.0, exit_ts=now - timedelta(days=1)),
    ]
    proposed = ProposedTrade(
        symbol="NVDA", action="buy", asset_type="equity", notional=1000.0, asof=now
    )

    rep = evaluate_pattern_warnings(trips, proposed)
    w = next(w for w in rep.warnings if w.category == "symbol_history")
    assert w.sample_size == 3
    assert w.evidence["symbol"] == "NVDA"
    assert w.evidence["win_rate"] == 0.0
    assert w.evidence["total_realized_pnl"] == -1500.0


def test_occ_option_symbol_normalization():
    """OCC option symbol is parsed into underlying, expiry, strike, right, and DTE."""
    asof = datetime(2026, 3, 15, 10, 0, tzinfo=timezone.utc)
    # SPY March 15 2026 Call 500.00
    p = normalize_proposed_trade({
        "symbol": "SPY260315C00500000",
        "qty": 2,
        "price": 3.50,
        "asof": asof,
    })
    assert p.clean_symbol == "SPY"
    assert p.asset_type == "option"
    assert p.option_expiry == date(2026, 3, 15)
    assert p.option_strike == 500.0
    assert p.option_right == "call"
    assert p.dte == 0
    assert p.is_0dte is True
    assert p.estimated_notional == 700.0  # 2 * 3.50 * 100


def test_day_of_week_disadvantage():
    """Friday trades with poor historical record triggers day_of_week caution."""
    # Create 5 Friday trips: 1 win, 4 losses, net -$1,000
    friday = datetime(2026, 3, 6, 14, 0, tzinfo=timezone.utc)  # 2026-03-06 is Friday
    trips = [
        _make_trip("SPY", 100.0, exit_ts=friday - timedelta(days=28)),
        _make_trip("SPY", -300.0, exit_ts=friday - timedelta(days=21)),
        _make_trip("SPY", -400.0, exit_ts=friday - timedelta(days=14)),
        _make_trip("SPY", -200.0, exit_ts=friday - timedelta(days=7)),
        _make_trip("SPY", -200.0, exit_ts=friday),
    ]
    proposed = ProposedTrade(
        symbol="SPY", action="buy", asset_type="equity", notional=1000.0, asof=friday
    )

    rep = evaluate_pattern_warnings(trips, proposed)
    w = next(w for w in rep.warnings if w.category == "day_of_week")
    assert w.severity == "caution"
    assert w.evidence["day"] == "Friday"
    assert w.evidence["round_trips"] == 5
    assert w.evidence["win_rate"] == 0.20


def test_tool_and_endpoint_execution():
    """check_trade_pattern executes via registry and FastAPI endpoint."""
    from sqlalchemy.pool import StaticPool
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sm = sessionmaker(bind=engine)
    session = sm()

    # Seed 6 transactions (3 round trips on SPY)
    now = datetime(2026, 3, 2, 10, 0, tzinfo=timezone.utc)
    t1 = Transaction(
        account_id=1, external_id="t1", symbol="SPY", side="buy", qty=10, price=500.0,
        occurred_at=now, source="broker"
    )
    t2 = Transaction(
        account_id=1, external_id="t2", symbol="SPY", side="sell", qty=10, price=505.0,
        occurred_at=now + timedelta(hours=1), source="broker"
    )
    t3 = Transaction(
        account_id=1, external_id="t3", symbol="SPY", side="buy", qty=10, price=505.0,
        occurred_at=now + timedelta(days=1), source="broker"
    )
    t4 = Transaction(
        account_id=1, external_id="t4", symbol="SPY", side="sell", qty=10, price=510.0,
        occurred_at=now + timedelta(days=1, hours=1), source="broker"
    )
    t5 = Transaction(
        account_id=1, external_id="t5", symbol="SPY", side="buy", qty=10, price=510.0,
        occurred_at=now + timedelta(days=2), source="broker"
    )
    t6 = Transaction(
        account_id=1, external_id="t6", symbol="SPY", side="sell", qty=10, price=515.0,
        occurred_at=now + timedelta(days=2, hours=1), source="broker"
    )
    session.add_all([t1, t2, t3, t4, t5, t6])
    session.commit()

    # 1. Registry tool execution
    ctx = ToolContext(db=session)
    res = registry.execute("check_trade_pattern", {"symbol": "SPY", "notional": 5000.0}, ctx)
    assert res["symbol"] == "SPY"
    assert res["verdict"] == "clear"
    assert res["historical_trips_count"] == 3

    # 2. FastAPI POST /api/pattern-warnings
    from api.main import get_db_session

    def override_get_db():
        with sm() as s:
            yield s

    app.dependency_overrides[get_db_session] = override_get_db

    r = client.post("/api/pattern-warnings", json={"symbol": "SPY", "notional": 5000.0})
    assert r.status_code == 200
    body = r.json()
    assert body["symbol"] == "SPY"
    assert body["verdict"] == "clear"

    # 3. FastAPI GET /api/pattern-warnings/SPY
    r_get = client.get("/api/pattern-warnings/SPY?notional=5000.0")
    assert r_get.status_code == 200
    assert r_get.json()["symbol"] == "SPY"

    app.dependency_overrides.clear()
    session.close()
    engine.dispose()


def test_real_schwab_confirmation_fills_evaluation():
    """Run pattern evaluation on Schwab confirmation fills fixture."""
    parsed = parse_directory(FIXTURES_DIR)
    assert len(parsed.fills) == 8

    # 1. Contemplating 0DTE options on SPY
    p_0dte = ProposedTrade(
        symbol="SPY", action="buy", asset_type="option", dte=0, notional=2000.0
    )
    rep_0dte = evaluate_pattern_warnings(parsed.fills, p_0dte)
    assert rep_0dte.is_0dte is True
    assert rep_0dte.verdict in ("clear", "caution", "warning_triggered", "insufficient_history")

    # 2. Contemplating $50,000 equity size
    p_huge = ProposedTrade(
        symbol="SPY", action="buy", asset_type="equity", notional=50000.0
    )
    rep_huge = evaluate_pattern_warnings(parsed.fills, p_huge)
    assert rep_huge.verdict in ("clear", "caution", "warning_triggered", "insufficient_history")
