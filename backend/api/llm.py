"""LLM provider abstraction (T041) — Anthropic and OpenAI behind one neutral interface.

Neutral message format (what the rest of KUBERA speaks):
  {"role": "user", "content": str}
  {"role": "assistant", "content": str | None, "tool_calls": [{"id", "name", "arguments"}]}
  {"role": "tool", "tool_call_id": str, "name": str, "content": str}

Neutral tool schema = registry.schemas() items: {"name", "description", "parameters"}.
Each adapter translates both directions; translation is the tested surface here.
No SDKs — thin httpx, same discipline as the broker clients.
"""

import json
from dataclasses import dataclass, field

import httpx

from settings import ConfigError, KuberaSettings, get_settings

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
MAX_TOKENS = 2048


class LLMError(RuntimeError):
    """Provider returned an error; message includes status and hint."""


@dataclass(frozen=True)
class ToolCallRequest:
    id: str
    name: str
    arguments: dict


@dataclass(frozen=True)
class LLMReply:
    text: str | None
    tool_calls: list[ToolCallRequest] = field(default_factory=list)
    stop_reason: str = "end"
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def wants_tools(self) -> bool:
        return len(self.tool_calls) > 0


def _post(url: str, headers: dict, payload: dict, provider: str,
          transport: httpx.BaseTransport | None) -> dict:
    try:
        with httpx.Client(timeout=120.0, transport=transport) as http:
            resp = http.post(url, headers=headers, json=payload)
    except httpx.HTTPError as e:
        raise LLMError(f"Network error calling {provider}: {e!r}") from e
    if resp.status_code == 401:
        raise LLMError(
            f"{provider} rejected the API key (401). Check the key in .env "
            f"({provider.upper()}_API_KEY) — regenerate if in doubt."
        )
    if resp.status_code >= 400:
        raise LLMError(f"{provider} failed: HTTP {resp.status_code} — {resp.text[:300]}")
    return resp.json()


class AnthropicProvider:
    def __init__(self, api_key: str, model: str,
                 transport: httpx.BaseTransport | None = None):
        self._key = api_key
        self.model = model
        self._transport = transport

    @staticmethod
    def _to_messages(neutral: list[dict]) -> list[dict]:
        out = []
        for m in neutral:
            if m["role"] == "user":
                out.append({"role": "user", "content": m["content"]})
            elif m["role"] == "assistant":
                blocks = []
                if m.get("content"):
                    blocks.append({"type": "text", "text": m["content"]})
                for tc in m.get("tool_calls", []):
                    blocks.append({"type": "tool_use", "id": tc["id"],
                                   "name": tc["name"], "input": tc["arguments"]})
                out.append({"role": "assistant", "content": blocks})
            elif m["role"] == "tool":
                out.append({"role": "user", "content": [{
                    "type": "tool_result", "tool_use_id": m["tool_call_id"],
                    "content": m["content"],
                }]})
            else:
                raise ValueError(f"unknown neutral role: {m['role']}")
        return out

    def complete(self, system: str, messages: list[dict], tools: list[dict]) -> LLMReply:
        payload = {
            "model": self.model,
            "max_tokens": MAX_TOKENS,
            "system": system,
            "messages": self._to_messages(messages),
        }
        if tools:
            payload["tools"] = [
                {"name": t["name"], "description": t["description"],
                 "input_schema": t["parameters"]}
                for t in tools
            ]
        d = _post(
            ANTHROPIC_URL,
            {"x-api-key": self._key, "anthropic-version": "2023-06-01"},
            payload, "anthropic", self._transport,
        )
        text_parts, calls = [], []
        for block in d.get("content", []):
            if block["type"] == "text":
                text_parts.append(block["text"])
            elif block["type"] == "tool_use":
                calls.append(ToolCallRequest(block["id"], block["name"], block["input"]))
        usage = d.get("usage", {})
        return LLMReply(
            text="".join(text_parts) or None,
            tool_calls=calls,
            stop_reason=d.get("stop_reason", "end"),
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
        )


class OpenAIProvider:
    """Speaks the OpenAI chat-completions wire format — which many providers serve
    (Ollama locally, Groq, Gemini's compatibility endpoint). `base_url` picks the host."""

    def __init__(self, api_key: str, model: str,
                 transport: httpx.BaseTransport | None = None,
                 base_url: str = "https://api.openai.com/v1"):
        self._key = api_key
        self.model = model
        self._transport = transport
        self._url = base_url.rstrip("/") + "/chat/completions"

    @staticmethod
    def _to_messages(system: str, neutral: list[dict]) -> list[dict]:
        out = [{"role": "system", "content": system}]
        for m in neutral:
            if m["role"] == "user":
                out.append({"role": "user", "content": m["content"]})
            elif m["role"] == "assistant":
                msg: dict = {"role": "assistant", "content": m.get("content")}
                if m.get("tool_calls"):
                    msg["tool_calls"] = [
                        {"id": tc["id"], "type": "function",
                         "function": {"name": tc["name"],
                                      "arguments": json.dumps(tc["arguments"])}}
                        for tc in m["tool_calls"]
                    ]
                out.append(msg)
            elif m["role"] == "tool":
                out.append({"role": "tool", "tool_call_id": m["tool_call_id"],
                            "content": m["content"]})
            else:
                raise ValueError(f"unknown neutral role: {m['role']}")
        return out

    def complete(self, system: str, messages: list[dict], tools: list[dict]) -> LLMReply:
        payload: dict = {"model": self.model,
                         "messages": self._to_messages(system, messages)}
        if tools:
            payload["tools"] = [
                {"type": "function",
                 "function": {"name": t["name"], "description": t["description"],
                              "parameters": t["parameters"]}}
                for t in tools
            ]
        d = _post(self._url, {"Authorization": f"Bearer {self._key}"},
                  payload, "openai", self._transport)
        msg = d["choices"][0]["message"]
        calls = [
            ToolCallRequest(tc["id"], tc["function"]["name"],
                            json.loads(tc["function"]["arguments"] or "{}"))
            for tc in (msg.get("tool_calls") or [])
        ]
        usage = d.get("usage", {})
        return LLMReply(
            text=msg.get("content"),
            tool_calls=calls,
            stop_reason=d["choices"][0].get("finish_reason", "end"),
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
        )


def build_provider(settings: KuberaSettings | None = None,
                   transport: httpx.BaseTransport | None = None):
    """Pick and validate the configured provider (fail-fast, actionable errors)."""
    s = settings or get_settings()
    provider = (s.llm_provider or "anthropic").lower()
    if provider == "anthropic":
        if not s.anthropic_api_key or not s.anthropic_api_key.get_secret_value():
            raise ConfigError(
                "LLM provider 'anthropic' selected but ANTHROPIC_API_KEY is missing "
                "in .env. Add it, or set LLM_PROVIDER=openai."
            )
        return AnthropicProvider(s.anthropic_api_key.get_secret_value(),
                                 s.anthropic_model, transport)
    if provider == "openai":
        # Local/compat endpoints (e.g. Ollama) don't need a real key — allow a dummy.
        is_custom_endpoint = "api.openai.com" not in s.openai_base_url
        key = s.openai_api_key.get_secret_value() if s.openai_api_key else ""
        if not key and not is_custom_endpoint:
            raise ConfigError(
                "LLM provider 'openai' selected but OPENAI_API_KEY is missing in .env. "
                "Add it, set OPENAI_BASE_URL to a local endpoint (e.g. Ollama), or set "
                "LLM_PROVIDER=anthropic."
            )
        return OpenAIProvider(key or "not-needed", s.openai_model, transport,
                              base_url=s.openai_base_url)
    if provider in ("claude-sdk", "claude_sdk", "max"):
        if not s.claude_code_oauth_token:
            raise ConfigError(
                "LLM provider 'claude-sdk' selected but CLAUDE_CODE_OAUTH_TOKEN is "
                "missing in .env. Run `claude setup-token` once (uses your Claude "
                "Pro/Max login), paste the token into .env, and restart. Personal "
                "use only per Anthropic policy (see DECISIONS.md D012)."
            )
        from api.llm_claude_sdk import ClaudeSDKProvider  # lazy: optional dependency
        return ClaudeSDKProvider(s)
    raise ConfigError(
        f"unknown LLM_PROVIDER '{s.llm_provider}' — valid values: anthropic, openai, "
        "claude-sdk"
    )
