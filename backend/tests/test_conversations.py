"""T082a conversations index — ordering, snippets, counts, empty state."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from api.main import app, get_db_session
from data.conversations import SNIPPET_CHARS, list_conversations
from data.db import make_session_factory
from data.models import Base, ChatMessage, Conversation

client = TestClient(app)
T0 = datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc)


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with make_session_factory(engine)() as s:
        yield s
    engine.dispose()


def seed(db, created_min, msgs):
    """msgs: [(role, content, minute_offset)]"""
    c = Conversation(created_at=T0 + timedelta(minutes=created_min))
    db.add(c)
    db.flush()
    for role, content, off in msgs:
        db.add(ChatMessage(conversation_id=c.id, role=role, content=content,
                           created_at=T0 + timedelta(minutes=off),
                           tool_name="get_portfolio" if role == "tool" else None))
    db.commit()
    return c.id


def test_orders_by_last_activity_not_creation(db):
    old = seed(db, 0, [("user", "first ever question", 0),
                       ("assistant", "answer", 1),
                       ("user", "revived much later", 500)])   # old thread, new activity
    new = seed(db, 10, [("user", "newer thread", 11), ("assistant", "a", 12)])
    rows = list_conversations(db)
    assert [r.id for r in rows] == [old, new]     # revived thread sorts first
    assert rows[0].started_at < rows[1].started_at  # ...despite being older


def test_snippet_is_the_owners_first_words(db):
    cid = seed(db, 0, [
        ("user", "  should I   buy SPY today?  ", 0),
        ("tool", '{"summary": "irrelevant payload"}', 1),
        ("assistant", "Here is the analysis", 2),
        ("user", "and what about QQQ", 3),
    ])
    r = list_conversations(db)[0]
    assert r.id == cid
    assert r.snippet == "should I buy SPY today?"   # whitespace collapsed
    assert "payload" not in r.snippet               # never a tool row
    assert "analysis" not in r.snippet              # never the assistant


def test_long_snippet_is_trimmed_with_ellipsis(db):
    seed(db, 0, [("user", "x" * 300, 0)])
    r = list_conversations(db)[0]
    assert len(r.snippet) == SNIPPET_CHARS
    assert r.snippet.endswith("…")


def test_counts_split_turns_from_tools(db):
    seed(db, 0, [("user", "q", 0), ("assistant", "a", 1),
                 ("tool", "{}", 2), ("tool", "{}", 3), ("assistant", "a2", 4)])
    r = list_conversations(db)[0]
    assert r.message_count == 3       # user + 2 assistant
    assert r.tool_calls == 2          # evidence pulled


def test_empty_and_limit(db):
    assert list_conversations(db) == []
    for i in range(5):
        seed(db, i, [("user", f"q{i}", i)])
    assert len(list_conversations(db, limit=2)) == 2
    with pytest.raises(ValueError):
        list_conversations(db, limit=0)


def test_conversation_with_no_messages_is_skipped(db):
    db.add(Conversation(created_at=T0))     # created but never used
    db.commit()
    assert list_conversations(db) == []


def test_endpoint(db):
    seed(db, 0, [("user", "how is my portfolio?", 0), ("assistant", "fine", 1)])

    def db_override():
        yield db

    app.dependency_overrides[get_db_session] = db_override
    try:
        r = client.get("/api/conversations")
        assert r.status_code == 200
        body = r.json()
        assert body["count"] == 1
        assert body["conversations"][0]["snippet"] == "how is my portfolio?"
        assert body["asof"]
        assert client.get("/api/conversations?limit=0").status_code == 422
        assert client.get("/api/conversations?limit=999").status_code == 422
    finally:
        app.dependency_overrides.clear()
