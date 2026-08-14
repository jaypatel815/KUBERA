"""I013 (schema-dump guard) + I014 (LLM timeout resilience) — both from one owner
transcript: "I'd like to update the investment policy statement" got an 8-row table
of internal field names, and the 19k-char IPS brief that followed died with a raw
"Network error calling openai: ReadTimeout('timed out')" on screen.
"""

import httpx
import pytest

from api.chat import ensure_no_schema_dump, run_chat_turn
from api.llm import LLMError, LLMReply, OpenAIProvider, build_provider
from api.tools import ToolContext
from data.db import make_engine, make_session_factory
from data.models import Base, ChatMessage
from settings import KuberaSettings

# --- I013: the owner's transcript, verbatim shapes ---------------------------

OWNER_ASK = "I'd like to update the investment policy statement"

MENU_REPLY = (
    "I can update your Investment Policy Statement (IPS) right away — just let me "
    "know which fields you'd like to change. The IPS fields I can adjust are: "
    "| Field | What it controls | |-------|------------------| "
    "| **objectives** | High-level goals | "
    "| **target_annual_return_frac** | Desired annual return as a decimal | "
    "| **max_drawdown_frac** | Maximum acceptable drawdown | "
    "| **horizon_years** | Investment time horizon in years | "
    "| **risk_tolerance** | Broad tolerance level | "
    "| **prohibited_strategies** | Strategies you forbid | "
    "Please tell me which of these you want to modify."
)


def test_owner_menu_reply_is_flagged():
    out = ensure_no_schema_dump(MENU_REPLY, OWNER_ASK)
    assert "⚠ Pacing check" in out
    assert "in your own words" in out


def test_explicit_field_question_is_not_flagged():
    out = ensure_no_schema_dump(MENU_REPLY, "what fields can I change on my IPS?")
    assert "⚠" not in out


def test_user_speaking_schema_is_mirrored_not_flagged():
    user = "set max_drawdown_frac to 0.2 and horizon_years to 30"
    reply = ("Done pending confirmation: max_drawdown_frac -> 0.2, "
             "horizon_years -> 30, leaving target_annual_return_frac unchanged.")
    assert "⚠" not in ensure_no_schema_dump(reply, user)


def test_fewer_than_three_internal_names_pass():
    reply = "Your max drawdown limit (max_drawdown_frac) is 15%, horizon_years is 30."
    assert "⚠" not in ensure_no_schema_dump(reply, "what's my drawdown limit?")


def test_plain_conversational_reply_untouched():
    reply = "Sure — what would you like to change?"
    assert ensure_no_schema_dump(reply, OWNER_ASK) == reply


# --- I014: timeout configuration ----------------------------------------------

def test_timeout_default_and_env_override(monkeypatch):
    monkeypatch.delenv("KUBERA_LLM_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("LLM_TIMEOUT_SECONDS", raising=False)
    assert KuberaSettings(_env_file=None).llm_timeout_seconds == 300.0
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "45")
    assert KuberaSettings(_env_file=None).llm_timeout_seconds == 45.0


def test_build_provider_wires_timeout_through():
    s = KuberaSettings(_env_file=None, llm_provider="anthropic",
                       anthropic_api_key="sk-test", llm_timeout_seconds=77.0)
    assert build_provider(s).timeout == 77.0
    s2 = KuberaSettings(_env_file=None, llm_provider="openai",
                        openai_api_key="sk-test", llm_timeout_seconds=88.0)
    assert build_provider(s2).timeout == 88.0


def test_timeout_error_is_actionable_not_raw():
    def raise_timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    p = OpenAIProvider("sk-test", "gpt-test",
                       transport=httpx.MockTransport(raise_timeout), timeout=42.0)
    with pytest.raises(LLMError) as exc:
        p.complete("S", [{"role": "user", "content": "hi"}], [])
    msg = str(exc.value)
    assert "timeout" in msg and "42" in msg and "LLM_TIMEOUT_SECONDS" in msg
    assert "ReadTimeout(" not in msg  # no raw exception repr for the owner


# --- I014: a timed-out turn keeps the message and the thread ------------------

class TimeoutProvider:
    def complete(self, system, messages, tools):
        raise LLMError("timeout: openai did not answer within 120s (long prompts "
                       "on slow/local models can exceed this)")


class DownProvider:
    def complete(self, system, messages, tools):
        raise LLMError("Network error calling openai: ConnectError('refused')")


@pytest.fixture()
def db():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with make_session_factory(engine)() as s:
        yield s
    engine.dispose()


def test_timeout_turn_saves_message_and_apologizes(db):
    big = "Here is my full investment policy. " + "Aggressive growth. " * 900
    r = run_chat_turn(db, TimeoutProvider(), ToolContext(), big)
    assert r.stop_reason == "llm_error"
    assert "saved" in r.reply and "try again" in r.reply
    assert "LLM_TIMEOUT_SECONDS" in r.reply  # tells the owner the actual knob
    assert "ReadTimeout" not in r.reply
    rows = db.query(ChatMessage).order_by(ChatMessage.id).all()
    assert [m.role for m in rows] == ["user", "assistant"]
    assert rows[0].content.startswith("Here is my full investment policy.")
    assert "[truncated" not in rows[0].content  # the brief survives WHOLE


def test_recovery_replays_the_saved_brief(db):
    big = "My investment policy: aggressive growth, decade horizon. " * 100

    class Scripted:
        def __init__(self):
            self.seen = None

        def complete(self, system, messages, tools):
            self.seen = messages
            return LLMReply(text="Picking up where we left off.", stop_reason="end")

    r1 = run_chat_turn(db, TimeoutProvider(), ToolContext(), big)
    p2 = Scripted()
    r2 = run_chat_turn(db, p2, ToolContext(), "try again",
                       conversation_id=r1.conversation_id)
    assert r2.reply.startswith("Picking up")
    replayed = " ".join(m["content"] or "" for m in p2.seen)
    assert "aggressive growth, decade horizon" in replayed  # the brief came back


def test_network_error_gets_distinct_wording(db):
    r = run_chat_turn(db, DownProvider(), ToolContext(), "hello there")
    assert r.stop_reason == "llm_error"
    assert "couldn't be reached" in r.reply
    assert "ConnectError" not in r.reply
