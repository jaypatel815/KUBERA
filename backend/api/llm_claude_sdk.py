"""Claude Agent SDK provider (T046) — KUBERA chat on the owner's Claude subscription.

POLICY (D012): personal, single-user use of a Pro/Max subscription via the Agent SDK is
permitted by Anthropic; offering claude.ai login/limits to OTHER users is not. If KUBERA
is ever productized, this provider must be replaced with API-key auth.
Setup (owner, once): `claude setup-token` → put CLAUDE_CODE_OAUTH_TOKEN in .env.

Integration model: unlike the raw-API providers (where our chat loop executes tools),
the SDK runs its own agent loop. We bridge the T024 registry in as SDK tools, lock the
permission surface to ONLY those tools (no Bash/file access), and capture every tool
event + result into `last_tool_events` — a side channel the chat loop persists so the
spec §2.7 audit trail stays complete. `tool_context` is set by the chat loop before each
complete() call; the confirmation gate and every other registry rail applies unchanged.

The SDK is an optional dependency (lazy import): `pip install claude-agent-sdk`.
Parsing duck-types the stream (block.text / block.name+input / message.usage) so unit
tests run without the package and minor SDK type changes don't break us.
"""

import asyncio
import json
import os
from typing import Any

from api.tools import ConfirmationRequiredError, ToolContext, ToolError, registry
from settings import ConfigError, KuberaSettings

SDK_SERVER_NAME = "kubera"
BUILTIN_DENYLIST = ["Bash", "Read", "Write", "Edit", "Glob", "Grep", "WebSearch"]


def _load_sdk():
    try:
        import claude_agent_sdk  # noqa: PLC0415 - optional dependency, lazy on purpose
        return claude_agent_sdk
    except ImportError as e:
        raise ConfigError(
            "LLM provider 'claude-sdk' needs the Agent SDK: pip install claude-agent-sdk "
            "(then run `claude setup-token` once and put CLAUDE_CODE_OAUTH_TOKEN in .env)."
        ) from e


def render_history(messages: list[dict]) -> str:
    """Flatten neutral history into a transcript block for the SDK's one-shot prompt.
    Tool payloads are already budget-managed upstream (T044)."""
    lines = []
    for m in messages[:-1]:
        if m["role"] == "user":
            lines.append(f"User: {m['content']}")
        elif m["role"] == "assistant" and m.get("content"):
            lines.append(f"KUBERA: {m['content']}")
        elif m["role"] == "tool":
            lines.append(f"[tool {m.get('name', '?')} returned: {m.get('content', '')}]")
    current = messages[-1]["content"] if messages else ""
    if not lines:
        return current
    transcript = "\n".join(lines)
    return (
        f"Conversation so far:\n{transcript}\n\n"
        f"Current user message (respond to this): {current}"
    )


class ClaudeSDKProvider:
    """Duck-type compatible with the other providers' complete() contract."""

    def __init__(self, settings: KuberaSettings):
        self._settings = settings
        self.tool_context: ToolContext | None = None  # set by the chat loop per turn
        self.last_tool_events: list[dict] = []  # read + cleared by the chat loop

    # -- registry bridge -----------------------------------------------------

    def _make_sdk_tools(self, sdk) -> list[Any]:
        """Wrap every registry tool as an SDK tool; execution records audit events."""
        sdk_tools = []
        for schema in registry.schemas():
            name = schema["name"]

            def make_handler(tool_name: str):
                async def handler(args: dict) -> dict:
                    ctx = self.tool_context or ToolContext()
                    try:
                        result = registry.execute(tool_name, args, ctx)
                        asof = result.get("asof")
                        content = json.dumps(result, default=str)
                    except ConfirmationRequiredError as e:
                        asof, content = None, json.dumps(
                            {"confirmation_required": True, "message": str(e)}
                        )
                    except ToolError as e:
                        asof, content = None, json.dumps({"error": str(e)})
                    self.last_tool_events.append({
                        "id": f"sdk_{tool_name}_{len(self.last_tool_events)}",
                        "name": tool_name, "arguments": args, "content": content,
                        "asof": (asof.isoformat() if hasattr(asof, "isoformat")
                                 else asof),
                    })
                    return {"content": [{"type": "text", "text": content}]}
                return handler

            decorated = sdk.tool(name, schema["description"], schema["parameters"])(
                make_handler(name)
            )
            sdk_tools.append(decorated)
        return sdk_tools

    # -- provider contract ----------------------------------------------------

    def complete(self, system: str, messages: list[dict], tools: list[dict]):
        from api.llm import LLMReply  # local import to avoid cycles

        sdk = _load_sdk()
        if self._settings.claude_code_oauth_token:
            # The SDK subprocess reads the token from the process environment;
            # pydantic-settings loads .env without exporting, so export at call time.
            os.environ.setdefault(
                "CLAUDE_CODE_OAUTH_TOKEN",
                self._settings.claude_code_oauth_token.get_secret_value(),
            )
        self.last_tool_events = []
        server = sdk.create_sdk_mcp_server(
            name=SDK_SERVER_NAME, version="1.0.0", tools=self._make_sdk_tools(sdk)
        )
        allowed = [f"mcp__{SDK_SERVER_NAME}__{n}" for n in registry.names()]
        options = sdk.ClaudeAgentOptions(
            system_prompt=system,
            # Dict form per current Python reference; if the installed SDK version wants
            # a list, the live test on the owner's machine will surface it -> ISSUES.
            mcp_servers={SDK_SERVER_NAME: server},
            allowed_tools=allowed,
            disallowed_tools=list(BUILTIN_DENYLIST),
            permission_mode="dontAsk",
            max_turns=self._settings.claude_sdk_max_turns,
        )
        prompt = render_history(messages)

        async def run() -> tuple[str, int, int]:
            text_parts: list[str] = []
            usage_in = usage_out = 0
            async for message in sdk.query(prompt=prompt, options=options):
                for block in getattr(message, "content", []) or []:
                    text = getattr(block, "text", None)
                    if isinstance(text, str):
                        text_parts.append(text)
                usage = getattr(message, "usage", None)
                if usage is not None:  # dict in current SDK versions, object in others
                    if isinstance(usage, dict):
                        usage_in = usage.get("input_tokens", 0) or 0
                        usage_out = usage.get("output_tokens", 0) or 0
                    else:
                        usage_in = getattr(usage, "input_tokens", 0) or 0
                        usage_out = getattr(usage, "output_tokens", 0) or 0
            return "\n".join(t for t in text_parts if t), usage_in, usage_out

        text, usage_in, usage_out = asyncio.run(run())
        # SDK already executed tools internally; we never ask our loop to run more.
        return LLMReply(text=text or None, tool_calls=[], stop_reason="end",
                        input_tokens=usage_in, output_tokens=usage_out)
