"""Conversation index (T082a) — the list behind the Orb's sidebar.

`/api/chat/{id}` replays one thread; nothing could enumerate them. This module
answers "what have I asked KUBERA lately?" — newest activity first, each entry
carrying the snippet the owner would recognize: his OWN first words, never a
system prompt or a tool payload.
"""

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from data.models import ChatMessage, Conversation

SNIPPET_CHARS = 90


@dataclass(frozen=True)
class ConversationSummary:
    id: int
    started_at: str
    last_activity_at: str
    message_count: int      # user + assistant turns (tool rows excluded)
    tool_calls: int         # how much evidence this thread pulled
    snippet: str            # the owner's opening words, trimmed
    title: str | None


def _snippet(text: str | None) -> str:
    if not text:
        return "(no text)"
    flat = " ".join(text.split())
    return flat if len(flat) <= SNIPPET_CHARS else flat[:SNIPPET_CHARS - 1] + "…"


def list_conversations(db: Session, limit: int = 30) -> list[ConversationSummary]:
    """Newest ACTIVITY first (not creation — a revived old thread belongs on top)."""
    if limit < 1:
        raise ValueError("limit must be >= 1")
    rows = db.execute(
        select(
            Conversation.id,
            Conversation.created_at,
            Conversation.title,
            func.max(ChatMessage.created_at).label("last_at"),
            func.count(ChatMessage.id).label("total"),
        )
        .join(ChatMessage, ChatMessage.conversation_id == Conversation.id)
        .group_by(Conversation.id)
        .order_by(func.max(ChatMessage.created_at).desc())
        .limit(limit)
    ).all()

    out: list[ConversationSummary] = []
    for cid, created, title, last_at, _total in rows:
        first_user = db.execute(
            select(ChatMessage.content)
            .where(ChatMessage.conversation_id == cid, ChatMessage.role == "user")
            .order_by(ChatMessage.id)
            .limit(1)
        ).scalar_one_or_none()
        turns = db.execute(
            select(func.count(ChatMessage.id)).where(
                ChatMessage.conversation_id == cid,
                ChatMessage.role.in_(("user", "assistant")),
            )
        ).scalar_one()
        tools = db.execute(
            select(func.count(ChatMessage.id)).where(
                ChatMessage.conversation_id == cid, ChatMessage.role == "tool",
            )
        ).scalar_one()
        out.append(ConversationSummary(
            id=cid,
            started_at=created.isoformat(),
            last_activity_at=last_at.isoformat() if last_at else created.isoformat(),
            message_count=turns,
            tool_calls=tools,
            snippet=_snippet(first_user),
            title=title,
        ))
    return out
