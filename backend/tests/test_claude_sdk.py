"""Claude SDK provider (T046) — fully mocked: no SDK install, no subprocess, no network."""

import json
import sys
import types
from dataclasses import dataclass, field

import pytest
from sqlalchemy import select

from api.chat import run_chat_turn
from api.llm import build_provider
from api.llm_claude_sdk import ClaudeSDKProvider, render_history
from api.tools import ToolContext
from data.db import make_engine, make_session_factory
from data.models import Base, ChatMessage
from settings import ConfigError, KuberaSettings


def sdk_settings(**kw) -> KuberaSettings:
    return KuberaSettings(
        _env_file=None, llm_provider="claude-sdk",
        claude_code_oauth_token="sk-oauth-test", **kw,
    )


# --- provider selection -------------------------------------------------------

def test_build_provider_selects_sdk_and_failfast(monkeypatch):
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    p = build_provider(sdk_settings())
    assert isinstance(p, ClaudeSDKProvider)
    with pytest.raises(ConfigError) as exc:
        build_provider(KuberaSettings(_env_file=None, llm_provider="claude-sdk"))
    assert "setup-token" in str(exc.value)


# --- history rendering --------------------------------------------------------

def test_render_history_flattens_transcript():
    msgs = [
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "answer one"},
        {"role": "tool", "name": "get_portfolio", "content": "{}"},
        {"role": "user", "content": "second"},
    ]
    out = render_history(msgs)
    assert "User: first" in out and "KUBERA: answer one" in out
    assert "[tool get_portfolio" in out
    assert out.strip().endswith("Current user message (respond to this): second")


def test_render_history_single_message_is_bare():
    assert render_history([{"role": "user", "content": "hi"}]) == "hi"


# --- fake SDK ----------------------------------------------------------------

@dataclass
class FakeBlock:
    text: str | None = None


@dataclass
class FakeUsage:
    input_tokens: int = 100
    output_tokens: int = 40


@dataclass
class FakeAssistant:
    content: list = field(default_factory=list)


@dataclass
class FakeResult:
    content: list = field(default_factory=list)
    usage: FakeUsage | dict = field(default_factory=FakeUsage)


def install_fake_sdk(
    monkeypatch,
    captured: dict,
    call_tool: str | None = None,
    usage: FakeUsage | dict | None = None,
):
    """A claude_agent_sdk stand-in: records options, optionally invokes one KUBERA
    tool handler mid-stream (simulating the SDK's internal agent loop), then yields
    a final text + usage.

    `usage` selects the SHAPE of the final usage payload, because the real SDK has
    shipped both: an object with attributes, and a plain dict (the owner's live run
    reported 0/0 tokens until we handled the dict form). Pass a dict to exercise
    that path. It is a parameter rather than something a test patches in afterwards
    — reaching back into `sys.modules` to mutate the fake is both harder to read
    and untypeable, since `sys.modules` is declared `dict[str, ModuleType]` and a
    checker therefore refuses attribute assignment on whatever comes out of it.
    """
    mod = types.ModuleType("claude_agent_sdk")

    def tool(name, description, schema):
        def deco(fn):
            return types.SimpleNamespace(name=name, handler=fn)
        return deco

    def create_sdk_mcp_server(name, version, tools):
        captured["server_tools"] = {t.name: t.handler for t in tools}
        return types.SimpleNamespace(name=name)

    class ClaudeAgentOptions:
        def __init__(self, **kw):
            captured["options"] = kw

    async def query(prompt, options):
        captured["prompt"] = prompt
        if call_tool:
            handler = captured["server_tools"][call_tool]
            await handler({})  # SDK executes the bridged tool internally
        yield FakeAssistant(content=[FakeBlock(text="Grounded answer.")])
        yield FakeResult(usage=FakeUsage() if usage is None else usage)

    setattr(mod, "tool", tool)
    setattr(mod, "create_sdk_mcp_server", create_sdk_mcp_server)
    setattr(mod, "ClaudeAgentOptions", ClaudeAgentOptions)
    setattr(mod, "query", query)
    monkeypatch.setitem(sys.modules, "claude_agent_sdk", mod)


# --- complete(): lockdown + parsing ------------------------------------------

def test_complete_locks_down_and_parses(monkeypatch):
    captured: dict = {}
    install_fake_sdk(monkeypatch, captured)
    p = ClaudeSDKProvider(sdk_settings())
    reply = p.complete("SYSTEM", [{"role": "user", "content": "hello"}], [])

    opts = captured["options"]
    assert opts["system_prompt"] == "SYSTEM"
    assert opts["permission_mode"] == "dontAsk"
    assert opts["max_turns"] == 8
    assert "Bash" in opts["disallowed_tools"]
    assert all(a.startswith("mcp__kubera__") for a in opts["allowed_tools"])
    assert len(opts["allowed_tools"]) == 38  # every registry tool bridged, nothing else
    assert reply.text == "Grounded answer."
    assert reply.tool_calls == []  # SDK executes internally; our loop never re-runs
    assert reply.input_tokens == 100 and reply.output_tokens == 40


def test_usage_parsed_from_dict_shape(monkeypatch):
    """Owner's live run showed 0/0 usage: the real SDK returns usage as a dict."""
    captured: dict = {}
    install_fake_sdk(monkeypatch, captured,
                     usage={"input_tokens": 5415, "output_tokens": 1347})
    p = ClaudeSDKProvider(sdk_settings())
    reply = p.complete("S", [{"role": "user", "content": "hi"}], [])
    assert reply.input_tokens == 5415
    assert reply.output_tokens == 1347


def test_bridged_tool_execution_records_audit_event(monkeypatch):
    captured: dict = {}
    install_fake_sdk(monkeypatch, captured, call_tool="get_daily_bars")
    p = ClaudeSDKProvider(sdk_settings())
    p.tool_context = ToolContext()  # no market client -> ToolError path
    p.complete("S", [{"role": "user", "content": "bars?"}], [])
    assert len(p.last_tool_events) == 1
    ev = p.last_tool_events[0]
    assert ev["name"] == "get_daily_bars"
    assert "error" in json.loads(ev["content"])  # failure surfaced, not swallowed


def test_missing_sdk_gives_actionable_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "claude_agent_sdk", None)
    p = ClaudeSDKProvider(sdk_settings())
    with pytest.raises(ConfigError) as exc:
        p.complete("S", [{"role": "user", "content": "x"}], [])
    assert "pip install claude-agent-sdk" in str(exc.value)


# --- chat loop side channel ---------------------------------------------------

class FakeSideChannelProvider:
    """Any provider exposing tool_context/last_tool_events gets audited by the loop."""

    def __init__(self):
        self.tool_context = None
        self.last_tool_events = []

    def complete(self, system, messages, tools):
        from api.llm import LLMReply
        assert self.tool_context is not None  # loop must hand us the request ctx
        self.last_tool_events = [{
            "id": "sdk_1", "name": "get_portfolio", "arguments": {},
            "content": '{"summary": "ok"}', "asof": "2026-08-11T22:00:00+00:00",
        }]
        return LLMReply(text="Done, based on your portfolio.", stop_reason="end")


def test_chat_loop_persists_side_channel_events():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with make_session_factory(engine)() as db:
        r = run_chat_turn(db, FakeSideChannelProvider(), ToolContext(), "how am I doing?")
        rows = db.execute(select(ChatMessage).order_by(ChatMessage.id)).scalars().all()
        assert [m.role for m in rows] == ["user", "tool", "assistant"]
        assert rows[1].tool_name == "get_portfolio"
        assert r.tool_trail == [{"name": "get_portfolio", "arguments": {}}]
        assert "2026-08-11" in r.reply or "Data recency" in r.reply  # recency enforced
    engine.dispose()


# --- T100 / I017: the timeout knob must reach THIS provider too ---------------

def test_timeout_setting_reaches_the_sdk_provider():
    """I017: LLM_TIMEOUT_SECONDS wired both httpx providers and not this one —
    the owner's actual brain. The knob existed and did nothing."""
    p = ClaudeSDKProvider(sdk_settings(llm_timeout_seconds=42.0))
    assert p.timeout == 42.0


def test_a_hung_query_raises_LLMError_instead_of_hanging(monkeypatch):
    """A query that never finishes must fail with an actionable message.

    Without this the request hangs until something upstream gives up, and the
    I014 recovery path (which commits the user's message, then apologises) never
    runs — so the turn is lost rather than resumable.
    """
    import asyncio as _asyncio

    from api.llm import LLMError

    captured: dict = {}
    install_fake_sdk(monkeypatch, captured)
    mod = sys.modules["claude_agent_sdk"]

    async def never_finishes(prompt, options):
        await _asyncio.sleep(3600)
        yield FakeAssistant(content=[])          # pragma: no cover — never reached

    setattr(mod, "query", never_finishes)

    # settings enforce llm_timeout_seconds >= 10 (a 1s timeout would make KUBERA
    # useless on any real prompt), so set the attribute rather than fight the
    # validator — the enforcement path is what is under test, not the floor.
    p = ClaudeSDKProvider(sdk_settings())
    p.timeout = 0.05
    with pytest.raises(LLMError, match="claude-sdk did not answer within"):
        p.complete("S", [{"role": "user", "content": "hi"}], [])


def test_timeout_message_names_the_env_knob_like_the_other_providers():
    """Same wording as the httpx providers: the owner should not have to learn
    which brain produced the error to know what to change."""
    import asyncio as _asyncio
    import inspect

    from api import llm, llm_claude_sdk

    source = inspect.getsource(llm_claude_sdk)
    assert "LLM_TIMEOUT_SECONDS in .env" in source
    assert "LLM_TIMEOUT_SECONDS in .env" in inspect.getsource(llm)
    assert "asyncio.wait_for" in source or "wait_for" in source
    assert _asyncio is not None
