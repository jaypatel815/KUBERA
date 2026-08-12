"""T043: the confirmation gate and the recency post-check — rails as code."""

import json

import pytest
from pydantic import BaseModel
from sqlalchemy import select

from api.chat import ensure_recency_line, run_chat_turn
from api.llm import LLMReply, ToolCallRequest
from api.tools import (
    ConfirmationRequiredError,
    ToolContext,
    ToolRegistry,
)
from api.tools import (
    registry as global_registry,
)
from data.db import make_engine, make_session_factory
from data.models import Base, ChatMessage

# --- confirmation gate at the registry --------------------------------------

class NoArgs(BaseModel):
    pass


def make_gated_registry() -> ToolRegistry:
    r = ToolRegistry()

    @r.tool("place_test_order", "pretend order tool", NoArgs, requires_confirmation=True)
    def _handler(ctx, p):
        return {"placed": True}

    return r


def test_unconfirmed_context_is_blocked():
    r = make_gated_registry()
    with pytest.raises(ConfirmationRequiredError) as exc:
        r.execute("place_test_order", {}, ToolContext(confirmed=False))
    assert "cannot confirm on their behalf" in str(exc.value)


def test_confirmed_context_passes():
    r = make_gated_registry()
    assert r.execute("place_test_order", {}, ToolContext(confirmed=True)) == {"placed": True}


def test_confirmation_flags_are_exactly_as_intended():
    """Guard: state-changing tools require confirmation, read/research tools never do.
    Any new tool must land in the right set consciously."""
    gated = {name for name in global_registry.names()
             if global_registry.requires_confirmation(name)}
    assert gated == {"update_ips"}, gated


# --- recency post-check ------------------------------------------------------

def test_recency_footer_added_when_missing():
    out = ensure_recency_line(
        "AAPL looks fine.", {"get_symbol_briefing": "2026-08-11T20:00:00+00:00"}
    )
    assert "Data recency" in out
    assert "get_symbol_briefing asof 2026-08-11T20:00:00+00:00" in out


def test_recency_untouched_when_reply_has_date():
    reply = "As of 2026-08-11, AAPL is fine."
    assert ensure_recency_line(reply, {"t": "2026-08-11T20:00:00+00:00"}) == reply


def test_recency_untouched_when_no_tools_used():
    assert ensure_recency_line("Hello!", {}) == "Hello!"


# --- end to end through the chat loop ----------------------------------------

@pytest.fixture()
def db():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with make_session_factory(engine)() as s:
        yield s
    engine.dispose()


class Scripted:
    def __init__(self, script):
        self.script = script

    def complete(self, system, messages, tools):
        return self.script.pop(0)


def test_chat_loop_appends_recency_footer(db):
    """Model uses a tool but omits any date -> the footer is enforced by code."""
    p = Scripted([
        LLMReply(text=None, stop_reason="tool_use",
                 tool_calls=[ToolCallRequest("t1", "get_daily_bars",
                                             {"symbol": "AAPL", "days": 30})]),
        LLMReply(text="AAPL had a decent month.", stop_reason="end"),  # no date!
    ])
    import httpx
    from test_alpaca import paper_settings

    from data.market_data import MarketDataClient

    bars = {"symbol": "AAPL", "next_page_token": None,
            "bars": [{"t": "2026-08-01T04:00:00Z", "o": 1, "h": 1, "l": 1,
                      "c": 100.0, "v": 1},
                     {"t": "2026-08-02T04:00:00Z", "o": 1, "h": 1, "l": 1,
                      "c": 101.0, "v": 1}]}
    with MarketDataClient(settings=paper_settings(),
                          transport=httpx.MockTransport(
                              lambda r: httpx.Response(200, json=bars))) as m:
        r = run_chat_turn(db, p, ToolContext(market=m), "how was AAPL this month?")
    assert "AAPL had a decent month." in r.reply
    assert "Data recency: get_daily_bars asof" in r.reply


def test_chat_loop_confirmation_flow(db, monkeypatch):
    """A gated tool without confirm -> model is told confirmation_required; with
    confirm=True (from the request, not the model) -> tool executes."""
    from api import chat as chat_module

    gated = make_gated_registry()
    monkeypatch.setattr(chat_module, "registry", gated)

    script = [
        LLMReply(text=None, stop_reason="tool_use",
                 tool_calls=[ToolCallRequest("t1", "place_test_order", {})]),
        LLMReply(text="I need your confirmation to proceed.", stop_reason="end"),
    ]
    r1 = run_chat_turn(db, Scripted(script), ToolContext(confirmed=False), "buy it")
    tool_row = db.execute(
        select(ChatMessage).where(ChatMessage.role == "tool")
    ).scalar_one()
    assert json.loads(tool_row.content)["confirmation_required"] is True
    assert "confirmation" in r1.reply.lower()

    script2 = [
        LLMReply(text=None, stop_reason="tool_use",
                 tool_calls=[ToolCallRequest("t2", "place_test_order", {})]),
        LLMReply(text="Done — order placed.", stop_reason="end"),
    ]
    r2 = run_chat_turn(db, Scripted(script2), ToolContext(confirmed=True), "yes, confirm",
                       conversation_id=r1.conversation_id)
    rows = db.execute(
        select(ChatMessage).where(ChatMessage.role == "tool").order_by(ChatMessage.id)
    ).scalars().all()
    assert json.loads(rows[-1].content) == {"placed": True}
    assert r2.reply.startswith("Done")
