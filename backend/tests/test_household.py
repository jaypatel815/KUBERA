"""T152 — the household store: strict units, upserts as new observations,
manual-data staleness, CSV idempotency. Hand-picked values throughout."""

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from data.household import (
    HouseholdError,
    balance_is_stale,
    list_debts,
    list_flows,
    log_spending,
    remove_debt,
    spending_between,
    upsert_debt,
    upsert_flow,
)
from data.models import Base


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
    engine.dispose()


def test_percent_shaped_apr_is_refused_with_the_conversion_spelled_out(db):
    with pytest.raises(HouseholdError, match=r"0\.249"):
        upsert_debt(db, name="Visa", kind="credit_card", balance=3200.0,
                    apr_frac=24.9, min_payment=35.0)


def test_upsert_is_insert_then_update_and_restamps_asof(db):
    upsert_debt(db, name="Visa", kind="credit_card", balance=3200.0,
                apr_frac=0.249, min_payment=35.0, credit_limit=5000.0,
                balance_asof="2026-08-01")
    row = upsert_debt(db, name="Visa", kind="credit_card", balance=2900.0,
                      apr_frac=0.249, min_payment=35.0, credit_limit=5000.0,
                      balance_asof="2026-08-21")
    debts = list_debts(db)
    assert len(debts) == 1 and debts[0].balance == 2900.0
    assert row.balance_asof == "2026-08-21"  # a re-statement is a new observation


def test_debts_listed_highest_apr_first_for_avalanche_reading(db):
    upsert_debt(db, name="CarLoan", kind="loan", balance=9000.0,
                apr_frac=0.065, min_payment=250.0)
    upsert_debt(db, name="Visa", kind="credit_card", balance=3200.0,
                apr_frac=0.249, min_payment=35.0)
    assert [d.name for d in list_debts(db)] == ["Visa", "CarLoan"]


def test_manual_balance_goes_stale_after_a_statement_cycle(db):
    d = upsert_debt(db, name="Visa", kind="credit_card", balance=3200.0,
                    apr_frac=0.249, min_payment=35.0,
                    balance_asof="2026-07-01")
    assert balance_is_stale(d, today=date(2026, 8, 21)) is True   # 51 days
    assert balance_is_stale(d, today=date(2026, 7, 20)) is False  # 19 days


def test_due_day_29_plus_is_refused_by_name(db):
    with pytest.raises(HouseholdError, match="February"):
        upsert_debt(db, name="X", kind="loan", balance=1.0, apr_frac=0.1,
                    min_payment=1.0, due_day=31)


def test_remove_debt_reports_whether_it_existed(db):
    upsert_debt(db, name="Visa", kind="credit_card", balance=1.0,
                apr_frac=0.2, min_payment=1.0)
    assert remove_debt(db, "Visa") is True
    assert remove_debt(db, "Visa") is False


def test_flows_validate_direction_and_sign(db):
    upsert_flow(db, name="salary", direction="income", amount=5000.0)
    upsert_flow(db, name="rent", direction="expense", amount=1800.0,
                category="housing")
    with pytest.raises(HouseholdError, match="direction"):
        upsert_flow(db, name="x", direction="sideways", amount=1.0)
    with pytest.raises(HouseholdError, match="positive"):
        upsert_flow(db, name="y", direction="expense", amount=-5.0)
    assert [f.name for f in list_flows(db)] == ["rent", "salary"]  # expense<income sort


def test_spending_log_and_window(db):
    log_spending(db, amount=62.18, category="Groceries", on="2026-08-20")
    log_spending(db, amount=15.49, category="subscriptions", on="2026-08-21")
    rows = spending_between(db, "2026-08-20", "2026-08-21")
    assert [r.amount for r in rows] == [62.18, 15.49]
    assert rows[0].category == "groceries"  # normalized lowercase


def test_csv_import_key_makes_reimport_a_no_op(db):
    first = log_spending(db, amount=9.99, category="subscriptions",
                         on="2026-08-19", source="csv", import_key="stmt1:row7")
    dup = log_spending(db, amount=9.99, category="subscriptions",
                       on="2026-08-19", source="csv", import_key="stmt1:row7")
    assert first is not None and dup is None
    assert len(spending_between(db, "2026-08-19", "2026-08-19")) == 1
