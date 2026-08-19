"""T110a — holdout custody + experiment budgets. Every refusal named."""

import json

import pytest
from research.custody import (
    CustodyError,
    consume_holdout,
    freeze_holdout,
    guarded_symbols,
    open_budget,
    params_hash,
    record_attempt,
    unlock_holdout,
)
from test_paper_loop import db  # noqa: F811,F401

from data.models import HoldoutWindow

# ------------------------------------------------------------- custody


def test_full_lifecycle_frozen_unlocked_consumed(db):  # noqa: F811
    row = freeze_holdout(db, "h1", ["spy", "QQQ"], "2026-01-01", "2026-06-30")
    assert row.state == "frozen"
    assert json.loads(row.symbols_json) == ["QQQ", "SPY"]   # sorted, upper
    h = row.params_hash

    unlock_holdout(db, "h1", by="owner")
    done = consume_holdout(db, "h1", "sharpe 0.4 oos", evaluated_hash=h)
    assert done.state == "consumed"
    journal = json.loads(done.journal_json)
    assert [e["event"].split()[0] for e in journal] == ["frozen", "unlocked",
                                                        "consumed"]


def test_every_violation_refuses_with_names(db):  # noqa: F811
    freeze_holdout(db, "h1", ["SPY"], "2026-01-01", "2026-06-30")
    with pytest.raises(CustodyError, match="defined ONCE"):
        freeze_holdout(db, "h1", ["SPY"], "2026-01-01", "2026-06-30")
    with pytest.raises(CustodyError, match="still frozen"):
        consume_holdout(db, "h1", "r", evaluated_hash="x")
    unlock_holdout(db, "h1", by="owner")
    with pytest.raises(CustodyError, match="unlock works ONCE"):
        unlock_holdout(db, "h1", by="owner")
    with pytest.raises(CustodyError, match="did not run the window as"):
        consume_holdout(db, "h1", "r", evaluated_hash="wrong-hash")
    row = db.execute(
        __import__("sqlalchemy").select(HoldoutWindow)).scalars().one()
    consume_holdout(db, "h1", "the one result", evaluated_hash=row.params_hash)
    with pytest.raises(CustodyError, match="already consumed"):
        consume_holdout(db, "h1", "again", evaluated_hash=row.params_hash)
    with pytest.raises(CustodyError, match="no holdout named"):
        unlock_holdout(db, "ghost", by="owner")


def test_params_hash_pins_the_definition():
    a = params_hash(["spy", "qqq"], "2026-01-01", "2026-06-30")
    b = params_hash(["QQQ", "SPY"], "2026-01-01", "2026-06-30")
    assert a == b                                    # order/case-invariant
    c = params_hash(["SPY", "QQQ"], "2026-01-01", "2026-07-01")
    assert c != a                                    # a changed window is new


def test_guarded_symbols_until_consumed(db):  # noqa: F811
    freeze_holdout(db, "h1", ["SPY"], "2026-01-01", "2026-06-30")
    freeze_holdout(db, "h2", ["NVDA"], "2026-01-01", "2026-06-30")
    assert guarded_symbols(db) == frozenset({"SPY", "NVDA"})
    unlock_holdout(db, "h1", by="owner")
    assert "SPY" in guarded_symbols(db)              # unlocked still guarded
    row_hash = params_hash(["SPY"], "2026-01-01", "2026-06-30")
    consume_holdout(db, "h1", "done", evaluated_hash=row_hash)
    assert guarded_symbols(db) == frozenset({"NVDA"})


def test_freeze_validation(db):  # noqa: F811
    with pytest.raises(CustodyError, match="symbols and start"):
        freeze_holdout(db, "bad", [], "2026-01-01", "2026-06-30")
    with pytest.raises(CustodyError, match="symbols and start"):
        freeze_holdout(db, "bad2", ["SPY"], "2026-06-30", "2026-01-01")


# ------------------------------------------------------------- budgets


def test_budget_counts_failures_and_refuses_over(db):  # noqa: F811
    open_budget(db, "rev-1", max_attempts=3)
    r1 = record_attempt(db, "rev-1", "failed", "bad seed")
    assert (r1.attempt_number, r1.remaining) == (1, 2)
    record_attempt(db, "rev-1", "failed")
    r3 = record_attempt(db, "rev-1", "ok")
    assert r3.remaining == 0
    with pytest.raises(CustodyError, match="used its budget"):
        record_attempt(db, "rev-1", "ok", "one more try")


def test_budget_preregistration_rules(db):  # noqa: F811
    open_budget(db, "rev-1", 2)
    with pytest.raises(CustodyError, match="set once"):
        open_budget(db, "rev-1", 10)                 # no mid-run raises
    with pytest.raises(CustodyError, match="ban, not a budget"):
        open_budget(db, "rev-2", 0)
    with pytest.raises(CustodyError, match="open_budget first"):
        record_attempt(db, "rev-3", "ok")
