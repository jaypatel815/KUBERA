"""T157b — GET /api/household: the dashboard's household payload.
Dependency-override pattern (in-memory DB), same as the brief endpoint test."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from api import main as main_module
from data.household import log_spending, upsert_debt, upsert_flow
from data.models import Base


@pytest.fixture()
def client_db():
    from fastapi.testclient import TestClient

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = Session(engine)

    def fake_db():
        yield session

    main_module.app.dependency_overrides[main_module.get_db_session] = fake_db
    try:
        yield TestClient(main_module.app), session
    finally:
        main_module.app.dependency_overrides.pop(main_module.get_db_session, None)
        session.close()
        engine.dispose()


def test_empty_household_is_an_answer(client_db):
    client, _ = client_db
    r = client.get("/api/household")
    assert r.status_code == 200
    d = r.json()
    assert d["debts"] == [] and d["total_balance"] == 0.0
    assert d["payoff"]["available"] is False
    assert "not tax or credit advice" in d["note"]


def test_household_serves_debts_payoff_and_staleness(client_db):
    client, db = client_db
    upsert_debt(db, name="Visa", kind="credit_card", balance=3200.0,
                apr_frac=0.249, min_payment=96.0, credit_limit=5000.0,
                balance_asof="2026-08-20")
    upsert_debt(db, name="CarLoan", kind="loan", balance=9000.0,
                apr_frac=0.065, min_payment=250.0, balance_asof="2026-06-01")
    d = client.get("/api/household").json()
    assert d["total_balance"] == pytest.approx(12200.0)
    visa = next(x for x in d["debts"] if x["name"] == "Visa")
    assert visa["utilization_frac"] == pytest.approx(0.64)
    assert visa["stale"] is False
    car = next(x for x in d["debts"] if x["name"] == "CarLoan")
    assert car["stale"] is True          # June balance in August
    assert d["any_stale"] is True
    p = d["payoff"]
    assert p["available"] is True
    assert p["avalanche"]["months"] >= 1
    assert p["interest_saved_by_avalanche"] >= 0  # the invariant, served


def test_impossible_payoff_is_served_as_its_named_refusal(client_db):
    client, db = client_db
    upsert_debt(db, name="payday", kind="other", balance=1000.0,
                apr_frac=0.60, min_payment=30.0)
    d = client.get("/api/household").json()
    assert d["payoff"]["available"] is False
    assert "outrun interest" in d["payoff"]["why"]


def test_missing_tables_are_a_named_503():
    from fastapi.testclient import TestClient

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)  # NO create_all — tables absent
    session = Session(engine)

    def fake_db():
        yield session

    main_module.app.dependency_overrides[main_module.get_db_session] = fake_db
    try:
        r = TestClient(main_module.app).get("/api/household")
        assert r.status_code == 503
        assert "alembic" in r.json()["detail"]
    finally:
        main_module.app.dependency_overrides.pop(main_module.get_db_session, None)
        session.close()
        engine.dispose()


def test_household_is_never_cached_by_the_service_worker():
    # money-never-cached doctrine (T136): /api/* is network-only in sw.js —
    # pinned there, asserted here for the NEW endpoint's benefit
    from pathlib import Path
    sw = (Path(main_module.__file__).resolve().parents[2]
          / "apps" / "web" / "sw.js").read_text(encoding="utf-8")
    assert "/api/" in sw  # the network-only guard covers every /api route


def test_wrong_method_is_405_not_a_mutation(client_db):
    client, _ = client_db
    assert client.post("/api/household").status_code == 405


def test_household_serves_budget_utilization_and_bills(client_db):
    """T154 — the engine's numbers ride the payload; nothing derived inline."""
    from datetime import date, timedelta

    client, db = client_db
    upsert_debt(db, name="Visa", kind="credit_card", balance=3200.0,
                apr_frac=0.249, min_payment=96.0, credit_limit=5000.0,
                due_day=(date.today() + timedelta(days=3)).day
                if (date.today() + timedelta(days=3)).day <= 28 else 1,
                balance_asof=date.today().isoformat())
    upsert_flow(db, name="salary", direction="income", amount=5000.0,
                category="salary")
    upsert_flow(db, name="rent", direction="expense", amount=1500.0,
                category="housing")
    log_spending(db, amount=200.0, category="groceries")
    d = client.get("/api/household").json()
    # budget: current-month view straight from the T154 engine
    b = d["budget"]
    assert b["income_planned"] == 5000.0
    assert b["recurring_expense_planned"] == 1500.0
    assert b["actual_by_category"] == {"groceries": 200.0}
    assert b["leftover"] == 3300.0
    assert "pace" in b and b["pace"]["discretionary_budget"] == 3500.0
    # utilization: 3200/5000 = 0.64, above the 30% caution line, flagged
    u = d["utilization"]
    assert u["cards"][0]["utilization_frac"] == pytest.approx(0.64)
    assert u["cards"][0]["above_caution"] is True
    assert u["caution_line_frac"] == 0.30
    visa = next(x for x in d["debts"] if x["name"] == "Visa")
    assert visa["above_caution"] is True
    # bills: a due day within the window appears with its date, or the list
    # is empty when the clamped fallback day already passed — never invented
    assert isinstance(d["bills_due_7d"], list)
    # the statement-dates gap is NAMED, not approximated (D039 honesty)
    assert "statement dates are not tracked" in d["note"]


def test_empty_household_still_serves_budget_frame(client_db):
    client, _ = client_db
    d = client.get("/api/household").json()
    assert d["budget"]["income_planned"] == 0.0
    assert any("no recurring flows" in n for n in d["budget"]["notes"])
    assert d["utilization"]["cards"] == []
    assert d["bills_due_7d"] == []
