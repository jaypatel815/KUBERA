"""Context assembly within a budget (T044) — deterministic, structure-preserving.

Why: the chat loop replays conversation history to the LLM every round. Unbounded
replay means unbounded cost. This module selects what the model sees, by rules:

1. History is grouped into BLOCKS that must live or die together — a lone message, or
   an assistant-with-tool-calls plus all of its tool results. Splitting those breaks
   the Anthropic/OpenAI message contracts (tool_use without tool_result = API error).
2. Blocks are kept newest-first until the character budget is exhausted; older blocks
   drop whole. The newest block is ALWAYS kept, budget be damned — the model must see
   the current turn.
3. In kept blocks older than the freshest KEEP_FULL_BLOCKS, tool-result payloads are
   elided (structure kept, content replaced by a stub). The assistant's own text —
   which summarizes those results — survives, so conclusions persist while bulky
   payloads age out.

Characters approximate tokens (~4:1); the budget is a setting, not a constant.
"""

import json
from typing import Sequence

DEFAULT_BUDGET_CHARS = 24_000
KEEP_FULL_BLOCKS = 4  # newest N blocks keep full tool payloads

_ELIDED_STUB = '{"elided": true, "note": "older tool result removed for context budget"}'


def _blocks(messages: Sequence[dict]) -> list[list[dict]]:
    """Group neutral messages into indivisible blocks."""
    out: list[list[dict]] = []
    i = 0
    while i < len(messages):
        m = messages[i]
        if m["role"] == "assistant" and m.get("tool_calls"):
            j = i + 1
            while j < len(messages) and messages[j]["role"] == "tool":
                j += 1
            out.append(list(messages[i:j]))
            i = j
        else:
            out.append([m])
            i += 1
    return out


def _size(block: list[dict]) -> int:
    return sum(len(json.dumps(m, default=str)) for m in block)


def assemble_context(
    messages: Sequence[dict], budget_chars: int = DEFAULT_BUDGET_CHARS
) -> list[dict]:
    """Select and slim history for the LLM. Deterministic; preserves message pairing."""
    if budget_chars < 1_000:
        raise ValueError(f"budget_chars must be >= 1000, got {budget_chars}")
    blocks = _blocks(messages)
    if not blocks:
        return []

    # 1-2. keep newest-first within budget; newest block unconditionally.
    kept: list[list[dict]] = [blocks[-1]]
    total = _size(blocks[-1])
    for block in reversed(blocks[:-1]):
        size = _size(block)
        if total + size > budget_chars:
            break
        kept.append(block)
        total += size
    kept.reverse()

    # 3. elide tool payloads in kept blocks older than the freshest KEEP_FULL_BLOCKS.
    cutoff = max(0, len(kept) - KEEP_FULL_BLOCKS)
    result: list[dict] = []
    for idx, block in enumerate(kept):
        for m in block:
            if idx < cutoff and m["role"] == "tool":
                m = {**m, "content": _ELIDED_STUB}
            result.append(m)
    return result
