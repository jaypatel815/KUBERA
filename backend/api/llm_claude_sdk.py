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
import logging
import os
from typing import Any

# Safe despite the apparent cycle: llm.py imports THIS module lazily, inside
# build_provider, so api.llm is always fully loaded before we are.
from api.llm import LLMError
from api.tool_policy import tool_names_for
from api.tools import ConfirmationRequiredError, ToolContext, ToolError, registry
from settings import ConfigError, KuberaSettings

log = logging.getLogger("kubera.claude_sdk")

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
        # I017: LLM_TIMEOUT_SECONDS reached both httpx providers and NOTHING here,
        # which is the owner's configured brain (I015). So the remediation offered
        # for I014 — "raise LLM_TIMEOUT_SECONDS" — was inert on his setup: a knob
        # he could turn that did nothing, which is worse than no knob at all.
        self.timeout = settings.llm_timeout_seconds
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
        sdk_tools = self._make_sdk_tools(sdk)
        server = sdk.create_sdk_mcp_server(
            name=SDK_SERVER_NAME, version="1.0.0", tools=sdk_tools
        )
        # T096: claude-sdk is a strong brain (gets everything under "auto"), but an
        # explicit KUBERA_TOOL_PROFILE=core still narrows what it may CALL. The
        # bridge always wraps the full registry; permission is the knob.
        offered = tool_names_for(self._settings, registry.names())
        allowed = [f"mcp__{SDK_SERVER_NAME}__{n}" for n in offered]
        # I011 diagnostic: if the bridge silently degrades (SDK version drift), the
        # model improvises tool names from prose — this line is the tell in the log.
        self.bridged_tool_count = len(sdk_tools)
        log.info("claude-sdk: bridged %d registry tools (%d allowed)",
                 len(sdk_tools), len(allowed))
        if len(sdk_tools) != len(registry.names()):
            log.warning("claude-sdk BRIDGE MISMATCH: %d sdk tools vs %d registry "
                        "tools — update claude-agent-sdk (I011)",
                        len(sdk_tools), len(registry.names()))
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

        async def run_with_deadline() -> tuple[str, int, int]:
            # asyncio.wait_for rather than an SDK option: the installed
            # claude-agent-sdk exposes no per-query timeout, and this works
            # regardless of SDK version. On expiry the generator is cancelled,
            # so no half-streamed text is returned as if it were complete.
            return await asyncio.wait_for(run(), timeout=self.timeout)

        try:
            text, usage_in, usage_out = asyncio.run(run_with_deadline())
        except (TimeoutError, asyncio.TimeoutError) as e:
            # Same wording as the httpx providers on purpose — the owner should
            # not have to learn which brain produced the message to know the fix.
            raise LLMError(
                f"timeout: claude-sdk did not answer within {self.timeout:.0f}s "
                f"(long prompts on slow models can exceed this — raise "
                f"LLM_TIMEOUT_SECONDS in .env)"
            ) from e
        # SDK already executed tools internally; we never ask our loop to run more.
        return LLMReply(text=text or None, tool_calls=[], stop_reason="end",
                        input_tokens=usage_in, output_tokens=usage_out)
