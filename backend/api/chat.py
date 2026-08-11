"""The conversation loop (T042): persona + history → LLM → tools → grounded answer.

Every user message, assistant reply, tool call, and tool result is persisted with a
timestamp — "why did KUBERA say that" is always answerable from chat_messages alone.
Tool failures are surfaced to the model verbatim (the persona requires honest reporting),
never swallowed. The loop is bounded: max_tool_rounds prevents runaway tool chains.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.persona import build_system_prompt
from api.tools import ToolContext, ToolError, registry
from data.models import ChatMessage, Conversation

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

    system = build_system_prompt(
        datetime.now(timezone.utc).isoformat(), registry.names()
    )
    schemas = registry.schemas()
    trail: list[dict] = []
    total_in = total_out = 0
    reply = None

    for _round in range(max_tool_rounds):
        history = _history(db, conversation_id)
        reply = provider.complete(system, history, schemas)
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
                conversation_id=conversation_id, reply=reply.text or "",
                tool_trail=trail, input_tokens=total_in, output_tokens=total_out,
                stop_reason=reply.stop_reason,
            )

        for tc in reply.tool_calls:
            trail.append({"name": tc.name, "arguments": tc.arguments})
            try:
                result = registry.execute(tc.name, tc.arguments, ctx)
                content = _cap(json.dumps(result, default=str))
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
        reply=(reply.text if reply and reply.text else
               f"(stopped after {max_tool_rounds} tool rounds without a final answer)"),
        tool_trail=trail, input_tokens=total_in, output_tokens=total_out,
        stop_reason="max_tool_rounds",
    )
