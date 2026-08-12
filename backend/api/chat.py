"""The conversation loop (T042): persona + history → LLM → tools → grounded answer.

Every user message, assistant reply, tool call, and tool result is persisted with a
timestamp — "why did KUBERA say that" is always answerable from chat_messages alone.
Tool failures are surfaced to the model verbatim (the persona requires honest reporting),
never swallowed. The loop is bounded: max_tool_rounds prevents runaway tool chains.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.context import assemble_context
from api.persona import build_system_prompt
from api.tools import ConfirmationRequiredError, ToolContext, ToolError, registry
from data.ips import format_ips_for_prompt, get_ips
from data.models import ChatMessage, Conversation
from settings import get_settings

log = logging.getLogger("kubera.chat")

MAX_TOOL_ROUNDS = 6
MAX_STORED_CHARS = 6000  # tool results are capped before storage and LLM replay


@dataclass(frozen=True)
class ChatTurnResult:
    conversation_id: int
    reply: str
    tool_trail: list[dict] = field(default_factory=list)  # [{"name", "arguments"}]
    input_tokens: int = 0
    output_tokens: int = 0
    stop_reason: str = "end"


def _cap(text: str, limit: int = MAX_STORED_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"... [truncated at {limit} chars]"


_RECENCY_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}|as of", re.IGNORECASE)


def ensure_recency_line(reply: str, tool_asofs: dict[str, str]) -> str:
    """Post-check (T043): a data-grounded reply must carry a date. If the model used
    tools but stated no recency, append a deterministic footer from the ACTUAL tool
    timestamps — enforced by code, not trusted to the prompt."""
    if not tool_asofs or _RECENCY_PATTERN.search(reply):
        return reply
    parts = "; ".join(f"{name} asof {asof}" for name, asof in sorted(tool_asofs.items()))
    return f"{reply}\n\n_Data recency: {parts}_"


def _history(db: Session, conversation_id: int) -> list[dict]:
    """DB rows -> neutral message format, oldest first."""
    rows = db.execute(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.id)
    ).scalars().all()
    neutral: list[dict] = []
    for r in rows:
        if r.role == "user":
            neutral.append({"role": "user", "content": r.content or ""})
        elif r.role == "assistant":
            m: dict = {"role": "assistant", "content": r.content}
            if r.tool_calls_json:
                m["tool_calls"] = json.loads(r.tool_calls_json)
            neutral.append(m)
        elif r.role == "tool":
            neutral.append({
                "role": "tool", "tool_call_id": r.tool_call_id or "",
                "name": r.tool_name or "", "content": r.content or "",
            })
    return neutral


def run_chat_turn(
    db: Session,
    provider,
    ctx: ToolContext,
    user_text: str,
    conversation_id: int | None = None,
    max_tool_rounds: int = MAX_TOOL_ROUNDS,
    voice: bool = False,
) -> ChatTurnResult:
    if not user_text.strip():
        raise ValueError("empty message")

    if conversation_id is None:
        convo = Conversation(title=_cap(user_text, 118))
        db.add(convo)
        db.flush()
        conversation_id = convo.id
    elif db.get(Conversation, conversation_id) is None:
        raise ValueError(f"unknown conversation_id {conversation_id}")

    db.add(ChatMessage(conversation_id=conversation_id, role="user", content=_cap(user_text)))
    db.commit()

    ips_row = get_ips(db)
    system = build_system_prompt(
        datetime.now(timezone.utc).isoformat(), registry.names(), voice=voice,
        ips_context=format_ips_for_prompt(ips_row) if ips_row else None,
    )
    schemas = registry.schemas()
    trail: list[dict] = []
    tool_asofs: dict[str, str] = {}  # tool name -> asof from its actual result
    total_in = total_out = 0
    reply = None

    # SDK-style providers execute tools inside complete(); hand them the request-bound
    # context (confirmation gate included) and collect their audit events afterward.
    if hasattr(provider, "tool_context"):
        provider.tool_context = ctx

    budget = get_settings().context_budget_chars
    for _round in range(max_tool_rounds):
        history = assemble_context(_history(db, conversation_id), budget)
        reply = provider.complete(system, history, schemas)

        for ev in (getattr(provider, "last_tool_events", None) or []):
            trail.append({"name": ev["name"], "arguments": ev["arguments"]})
            if ev.get("asof"):
                tool_asofs[ev["name"]] = ev["asof"]
            db.add(ChatMessage(
                conversation_id=conversation_id, role="tool",
                tool_call_id=ev["id"], tool_name=ev["name"],
                content=_cap(ev["content"]),
            ))
        if getattr(provider, "last_tool_events", None):
            provider.last_tool_events = []
            db.commit()
        total_in += reply.input_tokens
        total_out += reply.output_tokens

        db.add(ChatMessage(
            conversation_id=conversation_id, role="assistant",
            content=_cap(reply.text) if reply.text else None,
            tool_calls_json=json.dumps(
                [{"id": tc.id, "name": tc.name, "arguments": tc.arguments}
                 for tc in reply.tool_calls]
            ) if reply.wants_tools else None,
            input_tokens=reply.input_tokens, output_tokens=reply.output_tokens,
        ))
        db.commit()

        if not reply.wants_tools:
            return ChatTurnResult(
                conversation_id=conversation_id,
                reply=ensure_recency_line(reply.text or "", tool_asofs),
                tool_trail=trail, input_tokens=total_in, output_tokens=total_out,
                stop_reason=reply.stop_reason,
            )

        for tc in reply.tool_calls:
            trail.append({"name": tc.name, "arguments": tc.arguments})
            try:
                result = registry.execute(tc.name, tc.arguments, ctx)
                asof_val = result.get("asof")
                if asof_val is not None:  # str for most tools, datetime for dataclass dumps
                    tool_asofs[tc.name] = (
                        asof_val.isoformat() if hasattr(asof_val, "isoformat")
                        else str(asof_val)
                    )
                content = _cap(json.dumps(result, default=str))
            except ConfirmationRequiredError as e:
                # Not an error: the user must confirm out-of-band. Tell the model so it
                # can ask; it cannot confirm on the user's behalf (ctx is request-bound).
                content = json.dumps({"confirmation_required": True, "message": str(e)})
                log.info("tool %s awaiting user confirmation", tc.name)
            except ToolError as e:
                content = json.dumps({"error": str(e)})
                log.warning("tool %s failed in chat: %s", tc.name, e)
            db.add(ChatMessage(
                conversation_id=conversation_id, role="tool",
                tool_call_id=tc.id, tool_name=tc.name, content=content,
            ))
        db.commit()

    # Bounded loop exhausted: return honestly rather than spinning.
    return ChatTurnResult(
        conversation_id=conversation_id,
        reply=ensure_recency_line(
            (reply.text if reply and reply.text else
             f"(stopped after {max_tool_rounds} tool rounds without a final answer)"),
            tool_asofs,
        ),
        tool_trail=trail, input_tokens=total_in, output_tokens=total_out,
        stop_reason="max_tool_rounds",
    )
