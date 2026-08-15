"""T096 per-brain tool subsetting (from I008: small models drowned in the full
registry — asked for a ticker already named, claimed a live capability missing)."""


from api.tool_policy import (
    CORE_TOOLS,
    filter_schemas,
    is_small_brain,
    tool_names_for,
)
from api.tools import registry
from settings import KuberaSettings


def s(**kw) -> KuberaSettings:
    return KuberaSettings(_env_file=None, **kw)


# --- the guard that matters most ---------------------------------------------

def test_core_set_is_a_real_subset_of_the_registry():
    """A renamed tool must not silently vanish from small brains."""
    names = set(registry.names())
    missing = [t for t in CORE_TOOLS if t not in names]
    assert missing == [], f"CORE_TOOLS names not in registry: {missing}"
    assert len(CORE_TOOLS) < len(names)  # it is a SUBSET, not a copy


def test_core_covers_the_daily_conversation():
    for essential in ("get_portfolio", "get_symbol_briefing", "size_position",
                      "get_brief", "record_decision"):
        assert essential in CORE_TOOLS


# --- brain classification -----------------------------------------------------

def test_local_openai_endpoint_is_a_small_brain():
    assert is_small_brain(s(llm_provider="openai",
                            openai_base_url="http://localhost:11434/v1"))


def test_real_providers_are_strong():
    assert not is_small_brain(s(llm_provider="claude-sdk"))
    assert not is_small_brain(s(llm_provider="anthropic"))
    assert not is_small_brain(s(llm_provider="openai",
                                openai_base_url="https://api.openai.com/v1"))


# --- selection ----------------------------------------------------------------

ALL = registry.names()


def test_auto_curates_for_local_and_opens_for_strong():
    local = s(llm_provider="openai", openai_base_url="http://localhost:11434/v1")
    strong = s(llm_provider="claude-sdk")
    assert set(tool_names_for(local, ALL)) == set(CORE_TOOLS)
    assert tool_names_for(strong, ALL) == ALL


def test_profile_overrides_both_directions():
    local_forced_full = s(llm_provider="openai",
                          openai_base_url="http://localhost:11434/v1",
                          tool_profile="full")
    strong_forced_core = s(llm_provider="claude-sdk", tool_profile="core")
    assert tool_names_for(local_forced_full, ALL) == ALL
    assert set(tool_names_for(strong_forced_core, ALL)) == set(CORE_TOOLS)


def test_env_var_drives_the_profile(monkeypatch):
    monkeypatch.setenv("KUBERA_TOOL_PROFILE", "core")
    assert KuberaSettings(_env_file=None).tool_profile == "core"
    monkeypatch.delenv("KUBERA_TOOL_PROFILE")
    assert KuberaSettings(_env_file=None).tool_profile == "auto"


def test_filter_schemas_keeps_shape():
    local = s(llm_provider="openai", openai_base_url="http://localhost:11434/v1")
    out = filter_schemas(local, registry.schemas())
    assert {x["name"] for x in out} == set(CORE_TOOLS)
    assert all("parameters" in x and "description" in x for x in out)


# --- the chat loop honors it (and the prompt matches the offer) --------------

def test_chat_offers_core_to_a_local_brain(monkeypatch):
    from dataclasses import dataclass, field

    from api.chat import run_chat_turn
    from api.llm import LLMReply
    from api.tools import ToolContext
    from data.db import make_engine, make_session_factory
    from data.models import Base

    @dataclass
    class Scripted:
        calls: list = field(default_factory=list)

        def complete(self, system, messages, tools):
            self.calls.append({"system": system, "tools": tools})
            return LLMReply(text="ok", stop_reason="end")

    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    from settings import get_settings
    get_settings.cache_clear()
    try:
        engine = make_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        p = Scripted()
        with make_session_factory(engine)() as db:
            run_chat_turn(db, p, ToolContext(), "hello")
        offered = {t["name"] for t in p.calls[0]["tools"]}
        assert offered == set(CORE_TOOLS)
        # the persona must advertise exactly what was offered — no phantom tools
        system = p.calls[0]["system"]
        assert "get_portfolio" in system
        assert "get_correlation" not in system  # excluded tool never advertised
        engine.dispose()
    finally:
        get_settings.cache_clear()


def test_sdk_allowed_tools_respect_a_forced_core_profile(monkeypatch):
    """claude-sdk is strong (full by default) but an explicit profile still binds."""
    from test_claude_sdk import install_fake_sdk

    from api.llm_claude_sdk import ClaudeSDKProvider

    captured: dict = {}
    install_fake_sdk(monkeypatch, captured)
    settings = KuberaSettings(_env_file=None, llm_provider="claude-sdk",
                              claude_code_oauth_token="sk-oauth-test",
                              tool_profile="core")
    ClaudeSDKProvider(settings).complete(
        "S", [{"role": "user", "content": "hi"}], [])
    allowed = captured["options"]["allowed_tools"]
    assert len(allowed) == len(CORE_TOOLS)
    assert all(a.startswith("mcp__kubera__") for a in allowed)
    # the bridge still wraps everything; permission is the knob
    assert len(captured["server_tools"]) == len(registry.names())


def test_settings_rejects_nothing_but_documents_valid_values():
    # unknown profile falls back to "auto" behavior rather than crashing a session
    weird = s(llm_provider="claude-sdk", tool_profile="banana")
    assert tool_names_for(weird, ALL) == ALL
