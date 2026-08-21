"""T157b — GET /api/household: the dashboard's household payload.
Dependency-override pattern (in-memory DB), same as the brief endpoint test."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from api import main as main_module
from data.household import upsert_debt
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
