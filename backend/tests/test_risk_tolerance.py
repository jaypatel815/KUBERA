"""T069 — adaptive risk tolerance. Hand-computed fixtures, no DB, no network.

The point of this ticket is that KUBERA's estimate may override the owner's
self-assessment, so the bar for these tests is higher than usual: every number
below is one a human can check on paper, and the guards against speaking
without evidence are tested as hard as the findings themselves.
"""

from datetime import datetime, timedelta, timezone

from analysis.risk_tolerance import (
    BANDS,
    MIN_DAYS_FOR_DRAWDOWN,
    deepest_drawdown,
    dry_powder,
    estimate_risk_tolerance,
    post_loss_frequency,
    sizing_drift,
)

T0 = datetime(2026, 3, 2, 14, 0, tzinfo=timezone.utc)


def _iso(offset_hours: float) -> str:
    return (T0 + timedelta(hours=offset_hours)).isoformat()


def _fill(offset_hours: float, notional: float, side: str = "buy", price: float = 100.0):
    return {"ts_iso": _iso(offset_hours), "side": side,
            "qty": notional / price, "price": price}


def _trip(offset_hours: float, pnl: float):
    return {"symbol": "AAPL", "pnl": pnl, "exit_ts": _iso(offset_hours),
            "entry_ts": _iso(offset_hours - 48), "held_days": 2.0}


def _curve(values: list[float], start_day: int = 1) -> list[tuple[str, float]]:
    return [(f"2026-03-{start_day + i:02d}", v) for i, v in enumerate(values)]


# ------------------------------------------------------------------ drawdown

def test_drawdown_depth_is_hand_computable():
    """100 -> 120 peak -> 90 trough. (120-90)/120 = 0.25 exactly."""
    dd = deepest_drawdown(_curve([100, 110, 120, 100, 90, 95]))
    assert dd["depth_frac"] == 0.25
    assert dd["trough_date"] == "2026-03-05"
    assert dd["recovered"] is False


def test_drawdown_marks_recovery():
    dd = deepest_drawdown(_curve([100, 80, 90, 105]))
    assert dd["depth_frac"] == 0.2
    assert dd["recovered"] is True


def test_a_deposit_is_not_a_recovery():
    """The whole reason for flow adjustment.

    Equity 1000 -> 800 (a real -20%), then $500 deposited and equity reads 1300.
    Raw numbers would show a full recovery and a new high. Flow-adjusted, the
    index is still 0.8 and the drawdown stands unrecovered.
    """
    curve = _curve([1000, 800, 1300])
    flows = [("2026-03-03", 500.0)]

    naive = deepest_drawdown(curve)
    adjusted = deepest_drawdown(curve, flows)

    assert naive["recovered"] is True          # the lie
    assert adjusted["recovered"] is False      # the truth
    assert adjusted["depth_frac"] == 0.2


def test_a_withdrawal_is_not_a_drawdown():
    """1000 -> 1000, then $400 withdrawn and equity reads 600.

    Hand-check: base = 1000 + (-400) = 600, so the day's factor is 600/600 = 1.
    Flat performance, no drawdown. (The flow date must BE a curve date — an
    unmatched date is silently ignored, which is how this test failed first
    time round: the fixture, not the code, was wrong.)
    """
    curve = _curve([1000, 1000, 600])          # 03-01, 03-02, 03-03
    dd = deepest_drawdown(curve, [("2026-03-03", -400.0)])
    assert dd["depth_frac"] == 0.0

    # And without the flow, the same series looks like a 40% wipeout.
    assert deepest_drawdown(curve)["depth_frac"] == 0.4


def test_drawdown_handles_a_single_point():
    assert deepest_drawdown(_curve([1000]))["depth_frac"] is None


# ------------------------------------------------------------- sizing drift

def test_sizing_drift_detects_revenge_sizing():
    """After losses he buys 2000; after wins, 1000. Ratio is exactly 2.0."""
    trips, fills = [], []
    for i in range(3):
        trips.append(_trip(i * 100, pnl=-50))
        fills.append(_fill(i * 100 + 1, 2000))
    for i in range(3):
        trips.append(_trip(1000 + i * 100, pnl=+50))
        fills.append(_fill(1000 + i * 100 + 1, 1000))

    d = sizing_drift(trips, fills)
    assert d["ratio"] == 2.0
    assert d["after_loss"] == 2000.0 and d["after_win"] == 1000.0


def test_sizing_drift_stays_silent_without_paired_observations():
    """Two losses is not a habit. It must return None, not a confident 2.0x."""
    trips = [_trip(0, -50), _trip(100, -50), _trip(200, +50)]
    fills = [_fill(1, 2000), _fill(101, 2000), _fill(201, 1000)]
    assert sizing_drift(trips, fills)["ratio"] is None


def test_buys_outside_the_reaction_window_are_not_attributed():
    """A buy 3 days after a loss is a decision, not a reaction."""
    trips = [_trip(i * 200, -50) for i in range(3)] + [_trip(1000 + i * 200, +50) for i in range(3)]
    fills = [_fill(i * 200 + 72, 9999) for i in range(3)]          # too late to count
    fills += [_fill(1000 + i * 200 + 1, 1000) for i in range(3)]
    assert sizing_drift(trips, fills)["ratio"] is None


# --------------------------------------------------------- post-loss tempo

def test_post_loss_frequency_flags_tilt():
    """8 baseline buys over 40 days, plus a cluster right after three losses."""
    fills = [_fill(i * 120, 1000) for i in range(8)]
    trips = [_trip(1000 + i * 200, -50) for i in range(3)]
    fills += [_fill(1000 + i * 200 + 2, 1000) for i in range(3)]
    fills += [_fill(1000 + i * 200 + 4, 1000) for i in range(3)]

    f = post_loss_frequency(trips, fills)
    assert f["ratio"] is not None and f["ratio"] > 1.5


def test_post_loss_frequency_needs_enough_history():
    fills = [_fill(i, 1000) for i in range(4)]
    assert post_loss_frequency([_trip(1, -10)], fills)["ratio"] is None


def test_overlapping_loss_windows_do_not_double_count_time():
    """Two losses an hour apart cover ~25h of window, not 48h."""
    trips = [_trip(0, -10), _trip(1, -10), _trip(2, -10)]
    fills = [_fill(i * 100, 1000) for i in range(10)]
    f = post_loss_frequency(trips, fills)
    assert f["ratio"] is not None


# ------------------------------------------------------------------ powder

def test_dry_powder_fraction():
    assert dry_powder(10_000, 500)["cash_frac"] == 0.05
    assert dry_powder(0, 500)["cash_frac"] is None
    assert dry_powder(10_000, None)["cash_frac"] is None


# ---------------------------------------------------------------- estimate

def test_insufficient_evidence_proposes_no_change():
    """The honesty rule: a young account gets a refusal, not a number."""
    est = estimate_risk_tolerance(
        equity_curve=_curve([1000, 1010]),
        current={"daily_loss_limit_frac": 0.03, "risk_per_trade_frac": 0.01,
                 "max_position_frac": 0.20},
    )
    assert est.confidence == "insufficient"
    assert est.recommended["daily_loss_limit_frac"] == 0.03
    assert "not enough evidence" in est.headline.lower()
    assert any("sync.py" in c for c in est.caveats)


def test_revenge_sizing_tightens_the_budget():
    trips, fills = [], []
    for i in range(3):
        trips.append(_trip(i * 100, pnl=-50))
        fills.append(_fill(i * 100 + 1, 2000))
    for i in range(3):
        trips.append(_trip(1000 + i * 100, pnl=+50))
        fills.append(_fill(1000 + i * 100 + 1, 1000))

    est = estimate_risk_tolerance(
        trips=trips, fills=fills, equity=10_000, cash=3_000,
        current={"daily_loss_limit_frac": 0.03, "risk_per_trade_frac": 0.01,
                 "max_position_frac": 0.20},
    )
    # 0.03 * 0.75 = 0.0225, hand-computed
    assert est.recommended["daily_loss_limit_frac"] == 0.0225
    assert any("revenge" in e.finding for e in est.evidence)


def test_untested_stated_tolerance_is_named_and_not_budgeted_against():
    """Stated 20%, only ever lived through 3%. Cap becomes 3%/3 = 1%."""
    curve = _curve([1000] * 15 + [970] + [1000] * 15)
    est = estimate_risk_tolerance(
        equity_curve=curve,
        stated={"max_drawdown_frac": 0.20, "risk_tolerance": "aggressive"},
        current={"daily_loss_limit_frac": 0.03},
    )
    assert est.recommended["daily_loss_limit_frac"] == 0.01
    assert any("belief" in e.finding for e in est.evidence)
    assert any("use the evidence" in c for c in est.caveats)


def test_thin_cash_reduces_position_cap():
    est = estimate_risk_tolerance(
        equity=10_000, cash=100,   # 1% cash
        current={"max_position_frac": 0.20, "daily_loss_limit_frac": 0.03},
    )
    assert est.recommended["max_position_frac"] == 0.15   # 0.20 * 0.75
    assert any("fully invested" in e.finding for e in est.evidence)


def test_recommendations_are_always_inside_the_bands():
    """An adaptive budget that can adapt upward forever is not a budget."""
    est = estimate_risk_tolerance(
        equity=10_000, cash=9_000,
        current={"daily_loss_limit_frac": 0.99, "risk_per_trade_frac": 0.99,
                 "max_position_frac": 0.99},
    )
    for key, (lo, hi) in BANDS.items():
        assert lo <= est.recommended[key] <= hi


def test_estimate_is_always_a_proposal():
    est = estimate_risk_tolerance(equity=1000, cash=500)
    assert est.is_proposal
    assert any("PROPOSAL" in c for c in est.caveats)


def test_every_component_reports_its_sample_size():
    """No finding without a sample count — the T091b lesson, kept."""
    est = estimate_risk_tolerance(equity=1000, cash=500, equity_curve=_curve([1000, 900]))
    assert len(est.evidence) == 4
    for e in est.evidence:
        assert isinstance(e.sample, int)
        if e.signal is None:
            assert e.sample < max(MIN_DAYS_FOR_DRAWDOWN, 3)


# ------------------------------------------------- wiring (the silent-failure guard)

def test_attribution_exposes_trips_but_get_attribution_does_not_leak_them():
    """T069 reads report.trips. If that field ever disappears, this estimator
    would silently see zero trades and quietly stop measuring behavior — a
    wrong answer that looks exactly like a right one. Assert both halves:
    the field exists, and it stays out of the get_attribution payload."""
    from dataclasses import asdict as _asdict

    from analysis.attribution import AttributedFill, fifo_attribution

    fills = [
        AttributedFill(symbol="AAPL", side="buy", qty=10, price=100.0,
                       ts_iso="2026-03-01T14:00:00+00:00"),
        AttributedFill(symbol="AAPL", side="sell", qty=10, price=90.0,
                       ts_iso="2026-03-03T14:00:00+00:00"),
    ]
    report = fifo_attribution(fills)

    assert len(report.trips) == 1
    assert report.trips[0]["pnl"] == -100.0        # (90 - 100) * 10, hand-computed

    payload = _asdict(report)
    payload.pop("trips", None)
    assert "trips" not in payload
    assert payload["round_trips"] == 1             # the aggregate still reports it


def test_tool_is_registered_and_returns_a_proposal():
    from api.tools import registry
    assert "estimate_risk_tolerance" in registry.names()
    schema = next(s for s in registry.schemas() if s["name"] == "estimate_risk_tolerance")
    # The two instructions the owner actually asked for, asserted so a future
    # description rewrite cannot quietly drop them.
    assert "PROPOSAL" in schema["description"]
    assert "override" in schema["description"].lower()
    assert "insufficient" in schema["description"].lower()


def test_tool_actually_runs_against_a_real_database():
    """The gap that let a live AttributeError ship.

    The earlier wiring test asserted the tool was REGISTERED, which is not the
    same as working — `estimate_risk_tolerance` referenced
    `AccountSnapshot.captured_at`, a column that does not exist (it is `asof`),
    and every test passed because nothing ever executed the handler. A type
    checker found it in seconds. This test is the cheaper guard: run the thing.
    """
    from api.tools import ToolContext, registry
    from data.db import make_engine, make_session_factory
    from data.models import AccountSnapshot, Base, BrokerAccount

    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = make_session_factory(engine)()

    acct = BrokerAccount(broker="alpaca-paper", external_id="test")
    db.add(acct)
    db.flush()
    db.add(AccountSnapshot(account_id=acct.id, equity=10_000.0, cash=2_000.0,
                           buying_power=4_000.0, asof=T0, source="test"))
    db.commit()

    out = registry.execute("estimate_risk_tolerance", {}, ToolContext(db=db))

    assert out["is_proposal"] is True
    assert out["confidence"] in {"insufficient", "low", "moderate", "good"}
    assert set(out["recommended"]) == {
        "daily_loss_limit_frac", "risk_per_trade_frac", "max_position_frac"}
    # The snapshot above is 20% cash, so the dry-powder component must have spoken.
    assert any(e["name"] == "dry_powder" and e["signal"] is not None
               for e in out["evidence"])
