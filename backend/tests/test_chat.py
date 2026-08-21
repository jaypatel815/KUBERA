"""Chat loop (T042): scripted providers, real tool execution, full audit persistence."""

import json
from dataclasses import dataclass, field

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.pool import StaticPool
from test_alpaca import ACCOUNT_JSON, POSITIONS_JSON, paper_settings

from api.chat import run_chat_turn
from api.llm import LLMReply, ToolCallRequest
from api.main import (
    app,
    get_alpaca_client,
    get_db_session,
    get_llm_provider,
    get_market_client,
)
from api.tools import ToolContext
from data.alpaca import AlpacaClient
from data.db import make_engine, make_session_factory
from data.market_data import MarketDataClient
from data.models import Base, ChatMessage

client = TestClient(app)


@dataclass
class ScriptedProvider:
    """Pops scripted replies; records every complete() call for assertions."""

    script: list[LLMReply]
    calls: list[dict] = field(default_factory=list)

    def complete(self, system, messages, tools):
        self.calls.append({"system": system, "messages": list(messages), "tools": tools})
        return self.script.pop(0)


@pytest.fixture()
def db():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with make_session_factory(engine)() as s:
        yield s
    engine.dispose()


def alpaca_fake() -> AlpacaClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if "/v2/account" in request.url.path:
            return httpx.Response(200, json=ACCOUNT_JSON)
        return httpx.Response(200, json=POSITIONS_JSON)

    return AlpacaClient(settings=paper_settings(), transport=httpx.MockTransport(handler))


def test_text_only_turn_persists_and_returns(db):
    p = ScriptedProvider([LLMReply(text="Hello, Chotu.", stop_reason="end")])
    r = run_chat_turn(db, p, ToolContext(), "hi")
    assert r.reply == "Hello, Chotu."
    roles = [m.role for m in db.execute(select(ChatMessage)).scalars()]
    assert roles == ["user", "assistant"]
    assert "KUBERA" in p.calls[0]["system"]  # persona in place
    assert "VOICE MODE" not in p.calls[0]["system"]  # text mode by default
    assert len(p.calls[0]["tools"]) == 49  # registry schemas offered


def test_voice_flag_reaches_system_prompt(db):
    p = ScriptedProvider([LLMReply(text="About ten percent below its high.")])
    run_chat_turn(db, p, ToolContext(), "how's AAPL?", voice=True)
    assert "VOICE MODE" in p.calls[0]["system"]


def test_tool_round_executes_and_grounds_the_answer(db):
    p = ScriptedProvider([
        LLMReply(text=None, stop_reason="tool_use",
                 tool_calls=[ToolCallRequest("tc1", "get_portfolio", {})]),
        LLMReply(text="Equity is $100,000.75 as of just now.", stop_reason="end"),
    ])
    with alpaca_fake() as a:
        r = run_chat_turn(db, p, ToolContext(alpaca=a), "how am I doing?")
    assert "100,000.75" in r.reply
    assert r.tool_trail == [{"name": "get_portfolio", "arguments": {}}]
    rows = db.execute(select(ChatMessage).order_by(ChatMessage.id)).scalars().all()
    assert [m.role for m in rows] == ["user", "assistant", "tool", "assistant"]
    tool_row = rows[2]
    assert tool_row.tool_name == "get_portfolio"
    assert json.loads(tool_row.content)["summary"]["total_market_value"] == 1651.0
    # second LLM call saw the tool result in history
    second_call_msgs = p.calls[1]["messages"]
    assert second_call_msgs[-1]["role"] == "tool"
    assert "100000.75" in second_call_msgs[-1]["content"]


def test_tool_error_reported_not_swallowed(db):
    p = ScriptedProvider([
        LLMReply(text=None, stop_reason="tool_use",
                 tool_calls=[ToolCallRequest("tc1", "get_portfolio", {})]),
        LLMReply(text="I couldn't reach the account data.", stop_reason="end"),
    ])
    r = run_chat_turn(db, p, ToolContext(), "how am I doing?")  # no alpaca in ctx
    tool_row = db.execute(
        select(ChatMessage).where(ChatMessage.role == "tool")
    ).scalar_one()
    assert "error" in json.loads(tool_row.content)
    assert r.reply == "I couldn't reach the account data."


def test_runaway_tool_loop_is_bounded(db):
    endless = LLMReply(text=None, stop_reason="tool_use",
                       tool_calls=[ToolCallRequest("t", "get_portfolio", {})])
    p = ScriptedProvider([endless] * 3)
    r = run_chat_turn(db, p, ToolContext(), "spin forever", max_tool_rounds=3)
    assert r.stop_reason == "max_tool_rounds"
    assert "stopped after 3" in r.reply


def test_multi_turn_history_replayed(db):
    p1 = ScriptedProvider([LLMReply(text="First answer.")])
    r1 = run_chat_turn(db, p1, ToolContext(), "first question")
    p2 = ScriptedProvider([LLMReply(text="Second answer.")])
    r2 = run_chat_turn(db, p2, ToolContext(), "second question",
                       conversation_id=r1.conversation_id)
    assert r2.conversation_id == r1.conversation_id
    replayed = p2.calls[0]["messages"]
    assert replayed[0]["content"] == "first question"
    assert replayed[1]["content"] == "First answer."
    assert replayed[2]["content"] == "second question"


def test_unknown_conversation_rejected(db):
    with pytest.raises(ValueError):
        run_chat_turn(db, ScriptedProvider([]), ToolContext(), "hi", conversation_id=999)


def test_chat_endpoint_end_to_end():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = make_session_factory(engine)

    def db_override():
        with factory() as s:
            yield s

    def alpaca_override():
        a = alpaca_fake()
        try:
            yield a
        finally:
            a.close()

    def market_override():
        m = MarketDataClient(
            settings=paper_settings(),
            transport=httpx.MockTransport(lambda r: httpx.Response(404, json={})),
        )
        try:
            yield m
        finally:
            m.close()

    def provider_override():
        yield ScriptedProvider([
            LLMReply(text=None, stop_reason="tool_use",
                     tool_calls=[ToolCallRequest("tc1", "get_portfolio", {})]),
            LLMReply(text="You hold 10 AAPL; equity $100,000.75.", stop_reason="end"),
        ])

    app.dependency_overrides[get_db_session] = db_override
    app.dependency_overrides[get_alpaca_client] = alpaca_override
    app.dependency_overrides[get_market_client] = market_override
    app.dependency_overrides[get_llm_provider] = provider_override
    try:
        r = client.post(
            "/api/chat",
            json={"message": "how is my portfolio?", "conversation_id": 0},  # 0 == new
        )
        assert r.status_code == 200
        body = r.json()
        assert "AAPL" in body["reply"]
        # I010: "my portfolio" now auto-primes a server-side fetch (first trail
        # entry) before the model's own call — both are audited
        assert body["tool_calls"] == [
            {"name": "get_portfolio", "arguments": {"auto_primed": True}},
            {"name": "get_portfolio", "arguments": {}},
        ]
        assert body["conversation_id"] >= 1
        h = client.get(f"/api/chat/{body['conversation_id']}")
        assert h.status_code == 200
        assert [m["role"] for m in h.json()["messages"]] == \
            ["user", "assistant", "tool", "assistant"]
        missing = client.get("/api/chat/424242")
        assert missing.status_code == 404
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
