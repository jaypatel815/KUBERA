"""Voice-loop orchestration (T070) — the testable core behind scripts/talk.py.

Audio capture, speech-to-text, and text-to-speech are injected as plain callables so
this logic is fully unit-tested with fakes; the script wires real implementations.

Safety invariant (D015): confirmation is NEVER inferred from speech. The `confirm`
argument here comes from a deliberate TYPED gesture in the client, and is passed through
to ChatRequest.confirm untouched.
"""

import logging
from dataclasses import dataclass
from typing import Callable

log = logging.getLogger("kubera.voice")

# Injected callables:
#   transcriber(audio_bytes) -> str          (empty/whitespace = heard nothing)
#   chat_fn(text, conversation_id, confirm) -> {"conversation_id": int, "reply": str, ...}
#   speaker(text) -> None
Transcriber = Callable[[bytes], str]
ChatFn = Callable[[str, int | None, bool], dict]
Speaker = Callable[[str], None]

HEARD_NOTHING = "I didn't catch that — try again, a little closer to the microphone."


@dataclass
class VoiceState:
    """Threads the conversation across turns so KUBERA remembers the discussion."""

    conversation_id: int | None = None
    turns: int = 0


def run_voice_turn(
    audio: bytes,
    transcriber: Transcriber,
    chat_fn: ChatFn,
    speaker: Speaker,
    state: VoiceState,
    confirm: bool = False,
) -> dict:
    """One full turn: audio -> text -> KUBERA -> spoken reply. Returns a turn report."""
    text = (transcriber(audio) or "").strip()
    if not text:
        speaker(HEARD_NOTHING)
        return {"heard": "", "reply": HEARD_NOTHING, "chat_called": False,
                "conversation_id": state.conversation_id}

    response = chat_fn(text, state.conversation_id, confirm)
    state.conversation_id = response["conversation_id"]
    state.turns += 1
    reply = response.get("reply") or "(no reply)"
    speaker(reply)
    log.info("voice turn %d: heard=%r tools=%s", state.turns, text,
             [t["name"] for t in response.get("tool_calls", [])])
    return {"heard": text, "reply": reply, "chat_called": True,
            "conversation_id": state.conversation_id,
            "tool_calls": response.get("tool_calls", [])}
