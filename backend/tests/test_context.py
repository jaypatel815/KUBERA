"""Context assembly (T044) — every rule proven deterministically."""

import pytest

from api.context import _ELIDED_STUB, assemble_context


def user(text):
    return {"role": "user", "content": text}


def assistant(text):
    return {"role": "assistant", "content": text}


def tool_round(call_id, payload, text_after=None):
    """assistant tool_call + its tool result (+ optional final text) as flat messages."""
    msgs = [
        {"role": "assistant", "content": None,
         "tool_calls": [{"id": call_id, "name": "get_portfolio", "arguments": {}}]},
        {"role": "tool", "tool_call_id": call_id, "name": "get_portfolio",
         "content": payload},
    ]
    if text_after:
        msgs.append(assistant(text_after))
    return msgs


def test_short_history_passes_through_untouched():
    msgs = [user("hi"), assistant("hello")]
    assert assemble_context(msgs, 24_000) == msgs


def test_oldest_blocks_drop_first_newest_always_kept():
    pad = "x" * 2_000
    msgs = [user("A" + pad), assistant("B" + pad), user("C" + pad),
            assistant("D" + pad), user("current?")]
    out = assemble_context(msgs, budget_chars=5_000)
    # budget fits current + D + C; A and B (the oldest) drop
    assert out[-1]["content"] == "current?"
    assert len(out) == 3
    assert out[0]["content"].startswith("C")
    assert out[1]["content"].startswith("D")


def test_newest_block_kept_even_over_budget():
    huge_current = user("y" * 50_000)
    out = assemble_context([user("old"), huge_current], budget_chars=1_000)
    assert out == [huge_current]


def test_tool_pairing_never_split():
    """If an assistant tool_call is kept, its tool result must be too (and vice versa)."""
    msgs = [user("q1"), *tool_round("a", "r" * 3_000, "answer 1"),
            user("q2"), *tool_round("b", "r" * 3_000, "answer 2"),
            user("q3")]
    for budget in (1_000, 4_000, 8_000, 50_000):
        out = assemble_context(msgs, budget)
        for i, m in enumerate(out):
            if m["role"] == "assistant" and m.get("tool_calls"):
                assert i + 1 < len(out) and out[i + 1]["role"] == "tool", \
                    f"orphan tool_call at budget {budget}"
            if m["role"] == "tool":
                prev = out[i - 1]
                assert (prev.get("tool_calls") or prev["role"] == "tool"), \
                    f"orphan tool result at budget {budget}"


def test_old_tool_payloads_elided_new_ones_kept():
    # 6 blocks: [u, (a+t), a] [u, (a+t), a] -> tool payloads: old elided, recent full
    msgs = []
    for i in range(3):
        msgs.append(user(f"question {i}"))
        msgs.extend(tool_round(f"c{i}", f"PAYLOAD-{i}", f"answer {i}"))
    out = assemble_context(msgs, budget_chars=100_000)  # everything fits
    tool_msgs = [m for m in out if m["role"] == "tool"]
    assert len(tool_msgs) == 3
    # 9 blocks total, KEEP_FULL_BLOCKS=4 -> blocks 0..4 elide; first tool block is old
    assert tool_msgs[0]["content"] == _ELIDED_STUB
    assert tool_msgs[-1]["content"] == "PAYLOAD-2"  # newest stays full


def test_assistant_summaries_survive_elision():
    msgs = []
    for i in range(3):
        msgs.append(user(f"q{i}"))
        msgs.extend(tool_round(f"c{i}", "data", f"conclusion {i}"))
    out = assemble_context(msgs, 100_000)
    texts = [m["content"] for m in out if m["role"] == "assistant" and m["content"]]
    assert texts == ["conclusion 0", "conclusion 1", "conclusion 2"]


def test_budget_validation():
    with pytest.raises(ValueError):
        assemble_context([user("x")], budget_chars=10)


def test_empty_history():
    assert assemble_context([], 24_000) == []
