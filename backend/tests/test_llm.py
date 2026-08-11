"""LLM adapters (T041): translation in both directions, provider selection, errors.
No network — MockTransport captures exactly what would go over the wire."""

import json

import httpx
import pytest

from api.llm import AnthropicProvider, LLMError, OpenAIProvider, build_provider
from settings import ConfigError, KuberaSettings

NEUTRAL_HISTORY = [
    {"role": "user", "content": "How is my portfolio doing?"},
    {"role": "assistant", "content": "Let me check.",
     "tool_calls": [{"id": "tc1", "name": "get_portfolio", "arguments": {}}]},
    {"role": "tool", "tool_call_id": "tc1", "name": "get_portfolio",
     "content": '{"equity": 100000.75}'},
]

TOOLS = [{"name": "get_portfolio", "description": "Live portfolio.",
          "parameters": {"type": "object", "properties": {}}}]


def capture_transport(response_json: dict):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["payload"] = json.loads(request.content)
        return httpx.Response(200, json=response_json)

    return httpx.MockTransport(handler), captured


# --- Anthropic ----------------------------------------------------------------

ANTHROPIC_TOOLUSE_RESPONSE = {
    "content": [
        {"type": "text", "text": "Checking now."},
        {"type": "tool_use", "id": "tu_1", "name": "get_portfolio", "input": {}},
    ],
    "stop_reason": "tool_use",
    "usage": {"input_tokens": 120, "output_tokens": 30},
}


def test_anthropic_request_translation_and_parse():
    transport, cap = capture_transport(ANTHROPIC_TOOLUSE_RESPONSE)
    p = AnthropicProvider("sk-test", "claude-sonnet-5", transport)
    reply = p.complete("SYSTEM", NEUTRAL_HISTORY, TOOLS)

    payload = cap["payload"]
    assert payload["system"] == "SYSTEM"
    assert payload["tools"][0]["input_schema"] == TOOLS[0]["parameters"]
    # assistant turn became content blocks; tool result became user tool_result block
    assert payload["messages"][1]["content"][1]["type"] == "tool_use"
    assert payload["messages"][2]["content"][0]["type"] == "tool_result"
    assert payload["messages"][2]["content"][0]["tool_use_id"] == "tc1"
    assert cap["headers"]["x-api-key"] == "sk-test"

    assert reply.text == "Checking now."
    assert reply.wants_tools and reply.tool_calls[0].name == "get_portfolio"
    assert reply.stop_reason == "tool_use"
    assert reply.input_tokens == 120


# --- OpenAI -------------------------------------------------------------------

OPENAI_TOOLCALL_RESPONSE = {
    "choices": [{
        "message": {
            "content": None,
            "tool_calls": [{"id": "call_1", "type": "function",
                            "function": {"name": "get_portfolio", "arguments": "{}"}}],
        },
        "finish_reason": "tool_calls",
    }],
    "usage": {"prompt_tokens": 100, "completion_tokens": 20},
}


def test_openai_request_translation_and_parse():
    transport, cap = capture_transport(OPENAI_TOOLCALL_RESPONSE)
    p = OpenAIProvider("sk-test", "gpt-5", transport)
    reply = p.complete("SYSTEM", NEUTRAL_HISTORY, TOOLS)

    payload = cap["payload"]
    assert payload["messages"][0] == {"role": "system", "content": "SYSTEM"}
    assert payload["messages"][2]["tool_calls"][0]["function"]["name"] == "get_portfolio"
    assert payload["messages"][3]["role"] == "tool"
    assert payload["tools"][0]["function"]["parameters"] == TOOLS[0]["parameters"]
    assert cap["headers"]["authorization"] == "Bearer sk-test"

    assert reply.text is None
    assert reply.tool_calls[0].id == "call_1"
    assert reply.stop_reason == "tool_calls"


def test_openai_text_reply_parse():
    response = {"choices": [{"message": {"content": "All good."},
                             "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5}}
    transport, _ = capture_transport(response)
    reply = OpenAIProvider("k", "m", transport).complete("S", [
        {"role": "user", "content": "hi"}], [])
    assert reply.text == "All good." and not reply.wants_tools


# --- errors & selection -------------------------------------------------------

def test_401_actionable():
    transport = httpx.MockTransport(lambda r: httpx.Response(401, json={}))
    with pytest.raises(LLMError) as exc:
        AnthropicProvider("bad", "m", transport).complete("S", [
            {"role": "user", "content": "x"}], [])
    assert "401" in str(exc.value) and "ANTHROPIC_API_KEY" in str(exc.value)


def base_settings(**kw) -> KuberaSettings:
    return KuberaSettings(_env_file=None, **kw)


def test_openai_base_url_override_for_compat_endpoints():
    response = {"choices": [{"message": {"content": "local hello"},
                             "finish_reason": "stop"}], "usage": {}}
    transport, cap = capture_transport(response)
    p = OpenAIProvider("not-needed", "llama3.3", transport,
                       base_url="http://localhost:11434/v1")
    reply = p.complete("S", [{"role": "user", "content": "hi"}], [])
    assert cap["url"] == "http://localhost:11434/v1/chat/completions"
    assert reply.text == "local hello"


def test_build_provider_allows_keyless_custom_endpoint():
    s = base_settings(llm_provider="openai",
                      openai_base_url="http://localhost:11434/v1")
    p = build_provider(s)
    assert isinstance(p, OpenAIProvider)
    # but the real OpenAI endpoint still requires a key
    with pytest.raises(ConfigError):
        build_provider(base_settings(llm_provider="openai"))


def test_build_provider_selection_and_failfast():
    s = base_settings(llm_provider="anthropic", anthropic_api_key="k1")
    assert isinstance(build_provider(s), AnthropicProvider)
    s = base_settings(llm_provider="openai", openai_api_key="k2")
    assert isinstance(build_provider(s), OpenAIProvider)
    with pytest.raises(ConfigError) as exc:
        build_provider(base_settings(llm_provider="anthropic"))
    assert "ANTHROPIC_API_KEY" in str(exc.value)
    with pytest.raises(ConfigError) as exc2:
        build_provider(base_settings(llm_provider="carrier-pigeon"))
    assert "valid values" in str(exc2.value)


def test_unknown_neutral_role_rejected():
    with pytest.raises(ValueError):
        AnthropicProvider._to_messages([{"role": "wizard", "content": "x"}])
    with pytest.raises(ValueError):
        OpenAIProvider._to_messages("S", [{"role": "wizard", "content": "x"}])
