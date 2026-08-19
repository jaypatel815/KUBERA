"""T066 — trade coaching. Composer checks hand-walked; tool run end-to-end."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from test_paper_loop import db  # noqa: F401  (in-memory schema fixture)

from analysis.coaching import (
    compose_post_trade_review,
    compose_pre_trade_review,
)
from api.tools import ToolContext, ToolError, registry
from data.models import BrokerAccount, DecisionJournal, TradeReview, Transaction

T0 = datetime(2026, 3, 2, 14, 30, tzinfo=timezone.utc)


# ---------------------------------------------------------- pre-trade

def test_pre_trade_full_inputs_all_ok():
    r = compose_pre_trade_review(
        "aapl", "buy",
        thesis="range edge with rising RVOL", invalidation="close below 170",
        proposed_notional=5_000.0, equity=100_000.0, current_position_value=0.0,
        ips={"restrictions": ["TSLA"]},
        regime_label="range_bound", regime_confidence=0.7,
        pattern_verdict="clear", exit_plan_present=True,
    )
    assert r.symbol == "AAPL"
    assert r.attention_count == 0 and r.missing_count == 0
    assert r.sections["concentration"]["post_trade_weight_frac"] == pytest.approx(0.05)
    assert r.summary.startswith("6 ok")


def test_pre_trade_flags_the_dangerous_combination():
    """No invalidation + IPS-restricted + buying a downtrend + cap breach +
    pattern warning: every section that should object, objects."""
    r = compose_pre_trade_review(
        "TSLA", "buy",
        thesis="it will bounce",                      # no invalidation
        proposed_notional=25_000.0, equity=100_000.0,
        current_position_value=0.0,
        ips={"restrictions": ["TSLA", "GME"]},
        regime_label="trending_down", regime_confidence=0.8,
        pattern_verdict="warning_triggered",
        pattern_warnings=[{"category": "0dte", "severity": "high",
                           "headline": "h", "sample_size": 24}],
        exit_plan_present=False,
    )
    s = r.sections
    assert s["thesis"]["status"] == "attention"          # no invalidation
    assert s["ips_fit"]["status"] == "attention"
    assert s["ips_fit"]["restrictions_hit"] == ["TSLA"]
    assert s["concentration"]["status"] == "attention"   # 25% > 20% cap
    assert "EXCEEDS" in s["concentration"]["why"]
    assert s["regime_fit"]["status"] == "attention"      # buying a downtrend
    assert s["pattern_history"]["status"] == "attention"
    assert s["exit_plan"]["status"] == "missing"
    assert r.attention_count == 5 and r.missing_count == 1


def test_pre_trade_concentration_boundaries_hand_computed():
    """15k on 100k with 1k held = 16% -> early-warning band (attention);
    9k -> 10% -> ok. Cap math includes the existing position."""
    warn = compose_pre_trade_review(
        "X", "buy", proposed_notional=15_000.0, equity=100_000.0,
        current_position_value=1_000.0)
    assert warn.sections["concentration"]["status"] == "attention"
    assert warn.sections["concentration"]["post_trade_weight_frac"] == pytest.approx(0.16)
    ok = compose_pre_trade_review(
        "X", "buy", proposed_notional=9_000.0, equity=100_000.0,
        current_position_value=1_000.0)
    assert ok.sections["concentration"]["status"] == "ok"


def test_pre_trade_missing_inputs_name_their_suppliers():
    r = compose_pre_trade_review("X", "buy")
    s = r.sections
    assert s["thesis"]["status"] == "missing"
    assert "update_ips" in s["ips_fit"]["why"]
    assert "size_position" in s["concentration"]["why"]
    assert "get_regime" in s["regime_fit"]["why"]
    assert "check_trade_pattern" in s["pattern_history"]["why"]
    assert "get_exit_plan" in s["exit_plan"]["why"]
    assert r.missing_count == 6


def test_pre_trade_rejects_bad_side():
    with pytest.raises(ValueError, match="side"):
        compose_pre_trade_review("X", "hold")


# --------------------------------------------------------- post-trade

def _journal(**over):
    base = dict(id=7, verdict="buy", confidence=0.6, horizon_days=10,
                entry_price=100.0, target_price=115.0, stop_price=95.0,
                followed=True)
    base.update(over)
    return base


def test_post_trade_cut_winner_early_is_flagged():
    """Win exited at 2 of 10 horizon days (<25%) -> horizon attention."""
    trip = {"symbol": "AAPL", "pnl": 150.0, "held_days": 2.0,
            "entry_ts": T0.isoformat(), "exit_ts": (T0 + timedelta(days=2)).isoformat()}
    r = compose_post_trade_review(trip, _journal())
    assert r.sections["horizon"]["status"] == "attention"
    assert "cut-winners" in r.sections["horizon"]["why"]
    assert r.sections["follow_override"]["status"] == "ok"
    assert any("win of +150.00" in f for f in r.facts_for_lessons)


def test_post_trade_loser_past_its_clock_is_flagged():
    trip = {"symbol": "USO", "pnl": -200.0, "held_days": 25.0,
            "entry_ts": T0.isoformat(), "exit_ts": (T0 + timedelta(days=25)).isoformat()}
    r = compose_post_trade_review(trip, _journal(horizon_days=10))
    assert r.sections["horizon"]["status"] == "attention"
    assert "past its clock" in r.sections["horizon"]["why"] or \
           "twice the" in r.sections["horizon"]["why"]


def test_post_trade_unjournaled_is_the_finding():
    trip = {"symbol": "GME", "pnl": -50.0, "held_days": 1.0}
    r = compose_post_trade_review(trip, None)
    assert r.sections["journaling"]["status"] == "attention"
    assert any("without a journal entry" in f for f in r.facts_for_lessons)
    assert list(r.sections) == ["journaling"]     # nothing else judgeable


def test_post_trade_unmarked_decision_flagged_never_the_override():
    trip = {"symbol": "AAPL", "pnl": 80.0, "held_days": 8.0}
    unmarked = compose_post_trade_review(trip, _journal(followed=None))
    assert unmarked.sections["follow_override"]["status"] == "attention"
    overridden = compose_post_trade_review(trip, _journal(followed=False))
    assert overridden.sections["follow_override"]["status"] == "ok"
    assert "overridden" in overridden.sections["follow_override"]["why"]


# ----------------------------------------------------- tool end-to-end

def _seed_trip_and_journal(db):  # noqa: F811
    acct = BrokerAccount(broker="test", external_id="acc-1", currency="USD")
    db.add(acct)
    db.flush()
    db.add(DecisionJournal(symbol="AAPL", verdict="buy", confidence=0.6,
                           thesis="t", horizon_days=10, entry_price=100.0,
                           target_price=115.0, stop_price=95.0, followed=True,
                           ts=T0 - timedelta(hours=2)))
    for i, (side, price, when) in enumerate([("buy", 100.0, T0),
                                             ("sell", 110.0, T0 + timedelta(days=2))]):
        db.add(Transaction(account_id=acct.id, external_id=f"c{i}", symbol="AAPL",
                           side=side, qty=10.0, price=price, occurred_at=when,
                           source="test"))
    db.commit()


def test_tool_post_mode_end_to_end_and_persists(db):  # noqa: F811
    _seed_trip_and_journal(db)
    out = registry.execute("coach_trade", {"mode": "post", "symbol": "aapl"},
                           ToolContext(db=db))
    assert out["persisted"] is True
    assert out["trip"]["pnl"] == pytest.approx(100.0)   # 10 * (110-100)
    assert out["sections"]["journaling"]["status"] == "ok"
    assert out["sections"]["horizon"]["status"] == "attention"  # 2 of 10 days
    row = db.execute(select(TradeReview)).scalars().one()
    assert row.kind == "post" and row.symbol == "AAPL"
    assert row.journal_id == 1


def test_tool_pre_mode_persists_with_attention_count(db):  # noqa: F811
    out = registry.execute(
        "coach_trade",
        {"mode": "pre", "symbol": "AAPL", "side": "buy",
         "thesis": "range edge", "invalidation": "close below 170",
         "has_exit_plan": True},
        ToolContext(db=db))
    assert out["persisted"] is True
    # No alpaca/market in context: those sections are MISSING, never errors.
    assert out["sections"]["concentration"]["status"] == "missing"
    assert out["sections"]["regime_fit"]["status"] == "missing"
    row = db.execute(select(TradeReview)).scalars().one()
    assert row.kind == "pre"
    assert row.attention_count == out["attention_count"]


def test_tool_post_mode_names_known_symbols_when_absent(db):  # noqa: F811
    _seed_trip_and_journal(db)
    with pytest.raises(ToolError, match="AAPL"):
        registry.execute("coach_trade", {"mode": "post", "symbol": "MSFT"},
                         ToolContext(db=db))


def _coach_market_fake():
    """Valid OHLC (h >= c >= l) — test_briefing_tool's fixture has h=l=1 with
    c=100+, which the regime classifier rightly REJECTS; that rejection is
    itself pinned below."""
    import httpx
    from test_alpaca import paper_settings

    from data.market_data import MarketDataClient

    bars = {"symbol": "AAPL", "next_page_token": None, "bars": [
        {"t": f"2026-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}T04:00:00Z",
         "o": 100.0 + i, "h": 102.0 + i, "l": 99.0 + i, "c": 100.0 + i,
         "v": 1_000_000} for i in range(60)]}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=bars)

    return MarketDataClient(settings=paper_settings(),
                            transport=httpx.MockTransport(handler))


def test_tool_pre_mode_with_market_runs_the_regime_path(db):  # noqa: F811
    """Regression for the canary's catch: reading.regime (not .label). With
    valid bars the regime_fit section must be a real reading, not missing —
    this test executes the exact line that was wrong."""
    with _coach_market_fake() as m:
        out = registry.execute(
            "coach_trade",
            {"mode": "pre", "symbol": "AAPL", "side": "buy"},
            ToolContext(db=db, market=m))
    regime = out["sections"]["regime_fit"]
    assert regime["status"] != "missing", regime["why"]
    assert regime["regime"] in {"trending_up", "trending_down",
                                "range_bound", "breakout_watch"}


def test_tool_pre_mode_names_a_failed_regime_read(db):  # noqa: F811
    """A crashing market path must say the check FAILED — not pretend it was
    never attempted (the broad-except lesson from this ticket's own build)."""
    from test_briefing_tool import market_fake

    with market_fake() as m:  # h=l=1 vs c=100+: classifier rejects the bars
        out = registry.execute(
            "coach_trade",
            {"mode": "pre", "symbol": "AAPL", "side": "buy"},
            ToolContext(db=db, market=m))
    regime = out["sections"]["regime_fit"]
    assert regime["status"] == "missing"
    assert "FAILED" in regime["why"] and "ValueError" in regime["why"]
