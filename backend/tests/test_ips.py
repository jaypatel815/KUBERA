"""IPS (T061): storage, prompt formatting, chat injection, and the gated update tool."""

import pytest
from sqlalchemy import select  # noqa: F401 - parity with sibling test modules

from api.chat import run_chat_turn
from api.llm import LLMReply
from api.tools import ConfirmationRequiredError, ToolContext, registry
from data.db import make_engine, make_session_factory
from data.ips import format_ips_for_prompt, get_ips, upsert_ips
from data.models import Base


@pytest.fixture()
def db():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with make_session_factory(engine)() as s:
        yield s
    engine.dispose()


def seed_ips(db):
    return upsert_ips(
        db,
        objectives="long-term growth with capital preservation",
        target_annual_return_frac=0.12,
        max_drawdown_frac=0.15,
        horizon_years=10,
        risk_tolerance="moderate",
        restrictions=["never sell NVDA", "no crypto"],
    )


# --- storage -----------------------------------------------------------------

def test_upsert_creates_then_partially_updates(db):
    seed_ips(db)
    upsert_ips(db, max_drawdown_frac=0.10)  # partial: only drawdown changes
    row = get_ips(db)
    assert row.max_drawdown_frac == pytest.approx(0.10)
    assert row.objectives == "long-term growth with capital preservation"  # untouched
    assert "never sell NVDA" in row.restrictions_json


def test_restriction_lists_replace_wholesale(db):
    seed_ips(db)
    upsert_ips(db, restrictions=["no options"])
    row = get_ips(db)
    assert "no options" in row.restrictions_json
    assert "NVDA" not in row.restrictions_json


# --- prompt formatting -------------------------------------------------------

def test_format_contains_fields_and_hard_context_framing(db):
    text = format_ips_for_prompt(seed_ips(db))
    assert "INVESTMENT POLICY STATEMENT" in text
    assert "12.0%/yr" in text and "15.0%" in text and "10 years" in text
    assert "never sell NVDA; no crypto" in text
    assert "state conflicts plainly" in text


def test_format_empty_ips_is_empty_string(db):
    row = upsert_ips(db)  # nothing set
    assert format_ips_for_prompt(row) == ""


# --- chat injection ----------------------------------------------------------

class Scripted:
    def __init__(self, script):
        self.script, self.calls = script, []

    def complete(self, system, messages, tools):
        self.calls.append({"system": system})
        return self.script.pop(0)


def test_chat_injects_ips_when_set(db):
    seed_ips(db)
    p = Scripted([LLMReply(text="Noted.")])
    run_chat_turn(db, p, ToolContext(), "hello")
    assert "never sell NVDA" in p.calls[0]["system"]


def test_chat_omits_ips_when_unset(db):
    p = Scripted([LLMReply(text="Hello.")])
    run_chat_turn(db, p, ToolContext(), "hello")
    assert "INVESTMENT POLICY STATEMENT" not in p.calls[0]["system"]


# --- tools -------------------------------------------------------------------

def test_get_ips_tool_offers_setup_when_unset(db):
    out = registry.execute("get_ips", {}, ToolContext(db=db))
    assert out["ips"] is None and "update_ips" in out["note"]


def test_update_ips_requires_confirmation(db):
    with pytest.raises(ConfirmationRequiredError):
        registry.execute("update_ips", {"max_drawdown_frac": 0.15},
                         ToolContext(db=db, confirmed=False))
    assert get_ips(db) is None  # nothing changed


def test_update_ips_with_confirmation_persists(db):
    out = registry.execute(
        "update_ips",
        {"max_drawdown_frac": 0.15, "restrictions": ["no crypto"]},
        ToolContext(db=db, confirmed=True),
    )
    assert out["updated"] is True
    assert out["ips"]["max_drawdown_frac"] == pytest.approx(0.15)
    assert get_ips(db).max_drawdown_frac == pytest.approx(0.15)
