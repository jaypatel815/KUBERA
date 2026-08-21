"""T155 — household chat tools, RUN end-to-end against an in-memory DB
(D027 #1: call it, don't just assert it registered)."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from api.tools import ToolArgumentError, ToolContext, ToolError, registry
from data.models import Base


@pytest.fixture()
def db():
    engine = create_engine("sqlite://",
                           connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()
    engine.dispose()


def test_household_tools_are_registered():
    names = set(registry.names())
    assert {"add_debt", "log_spending", "add_recurring",
            "get_household"} <= names
    # writes are NOT confirmation-gated (owner-stated facts, strict store),
    # matching the update_watchlist precedent — update_ips stays the only gate
    for n in ("add_debt", "log_spending", "add_recurring"):
        assert registry.requires_confirmation(n) is False


def test_add_debt_converts_percent_to_fraction(db):
    out = registry.execute("add_debt", {
        "name": "Visa", "kind": "credit_card", "balance": 3200.0,
        "apr_percent": 24.9, "min_payment": 96.0, "credit_limit": 5000.0,
        "due_day": 25,
    }, ToolContext(db=db))
    assert out["recorded"] is True
    assert out["debt"]["apr_frac"] == 0.249          # 24.9% -> 0.249, proven
    assert "24.9% APR stored as fraction 0.249" in out["apr_note"]
    assert "as you told me on" in out["note"]        # recency phrasing seeded


def test_add_debt_refuses_fraction_smell_and_bad_kind(db):
    with pytest.raises(ToolArgumentError, match="looks like a fraction"):
        registry.execute("add_debt", {
            "name": "Visa", "balance": 100.0, "apr_percent": 0.249,
            "min_payment": 10.0}, ToolContext(db=db))
    # exactly 0 is a real promo APR — allowed
    out = registry.execute("add_debt", {
        "name": "Promo", "balance": 100.0, "apr_percent": 0,
        "min_payment": 10.0}, ToolContext(db=db))
    assert out["debt"]["apr_frac"] == 0.0
    with pytest.raises(ToolArgumentError, match="kind must be one of"):
        registry.execute("add_debt", {
            "name": "x", "kind": "mortgage?", "balance": 1.0,
            "apr_percent": 5.0, "min_payment": 1.0}, ToolContext(db=db))


def test_log_spending_and_add_recurring_round_trip(db):
    s = registry.execute("log_spending", {
        "amount": 40.0, "category": "Gas"}, ToolContext(db=db))
    assert s["entry"]["category"] == "gas"           # store lowercases
    r = registry.execute("add_recurring", {
        "name": "rent", "direction": "Expense", "amount": 1500.0,
        "category": "housing"}, ToolContext(db=db))
    assert r["flow"]["direction"] == "expense"       # lenient case handling
    with pytest.raises(ToolArgumentError):
        registry.execute("add_recurring", {
            "name": "x", "direction": "sideways", "amount": 1.0},
            ToolContext(db=db))


def test_get_household_composes_the_same_view_as_the_api(db):
    ctx = ToolContext(db=db)
    registry.execute("add_debt", {
        "name": "Visa", "kind": "credit_card", "balance": 3200.0,
        "apr_percent": 24.9, "min_payment": 96.0, "credit_limit": 5000.0,
    }, ctx)
    registry.execute("add_recurring", {
        "name": "salary", "direction": "income", "amount": 5000.0,
        "category": "salary"}, ctx)
    registry.execute("log_spending", {"amount": 200.0, "category": "groceries"}, ctx)
    out = registry.execute("get_household", {}, ctx)
    # the composed view = the /api/household payload (shared service, T155)
    assert out["total_balance"] == 3200.0
    assert out["payoff"]["available"] is True
    assert out["budget"]["income_planned"] == 5000.0
    assert out["budget"]["actual_by_category"] == {"groceries": 200.0}
    assert out["utilization"]["cards"][0]["above_caution"] is True  # 0.64
    assert "statement dates are not tracked" in out["note"]


def test_get_household_names_missing_tables():
    engine = create_engine("sqlite://",
                           connect_args={"check_same_thread": False},
                           poolclass=StaticPool)  # NO create_all
    session = Session(engine)
    try:
        with pytest.raises(ToolError, match="alembic"):
            registry.execute("get_household", {}, ToolContext(db=session))
    finally:
        session.close()
        engine.dispose()


def test_mcp_exposes_get_household_readonly_but_not_the_writes():
    from api.mcp_server import _READ_ONLY_TOOLS
    assert "get_household" in _READ_ONLY_TOOLS
    for n in ("add_debt", "log_spending", "add_recurring"):
        assert n not in _READ_ONLY_TOOLS
