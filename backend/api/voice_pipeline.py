"""T074b (sandbox half) — the Pipecat processor that keeps voice-KUBERA
the SAME KUBERA.

T074a's research decision: Pipecat locally, and the HARD part named in
the ticket is this seam — the realtime pipeline must route through OUR
/api/chat (context assembly, tool loop, confirmation rails, persona),
never through a raw LLM service that would bypass every rail. This module
is that seam: a FrameProcessor that takes finalized user utterances and
pushes KUBERA's reply text downstream toward TTS.

Probed against pipecat 0.0.108 (installed and introspected, not
recalled): TranscriptionFrame carries .text/.user_id/.timestamp;
process_frame(frame, direction); push_frame defaults DOWNSTREAM.

What stays owner-machine (T074b's other half): LocalAudioTransport, STT,
kokoro TTS wiring, latency and barge-in measurement. This half proves
the chat seam works and pins its contract; audio hardware cannot exist
in the sandbox and is not faked here.

Voice-specific behavior carried over from the chat layer: voice=True
rides the request so the persona answers ear-shaped, and the
conversation_id from the first reply is carried into every later turn —
a voice session is ONE conversation, not amnesia per utterance.
"""

from __future__ import annotations

import logging

import httpx

# pipecat ships in requirements-voice.txt only (like kokoro/soundfile) —
# absent from KUBERA's root venv and CI by design, so the type checker
# cannot see it there (I036 class, suppressed narrowly WITH the reason,
# proactively this time).
from pipecat.frames.frames import (  # pyrefly: ignore
    Frame,
    TextFrame,
    TranscriptionFrame,
)
from pipecat.processors.frame_processor import (  # pyrefly: ignore
    FrameDirection,
    FrameProcessor,
)

log = logging.getLogger("kubera.voice")

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
CHAT_TIMEOUT_S = 90.0   # matches the chat layer's own LLM patience (T100)


class KuberaChatProcessor(FrameProcessor):
    """TranscriptionFrame in -> POST /api/chat -> TextFrame(reply) out.

    Everything else passes through untouched (system frames keep the
    pipeline alive). Failures become a SPOKEN named degradation — a voice
    loop that dies silently mid-conversation is worse than one that says
    it lost the server."""

    def __init__(self, base_url: str = DEFAULT_BASE_URL,
                 client: httpx.AsyncClient | None = None, **kwargs):
        super().__init__(**kwargs)
        self._base_url = base_url.rstrip("/")
        self._client = client or httpx.AsyncClient(timeout=CHAT_TIMEOUT_S)
        self._conversation_id: int | None = None

    @property
    def conversation_id(self) -> int | None:
        return self._conversation_id

    async def process_frame(self, frame: Frame,
                            direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)
        if isinstance(frame, TranscriptionFrame) and frame.text.strip():
            await self._chat_turn(frame.text.strip())
            return
        await self.push_frame(frame, direction)

    async def _chat_turn(self, text: str) -> None:
        payload: dict = {"message": text, "voice": True}
        if self._conversation_id is not None:
            payload["conversation_id"] = self._conversation_id
        try:
            r = await self._client.post(f"{self._base_url}/api/chat",
                                        json=payload)
            r.raise_for_status()
            body = r.json()
        except httpx.HTTPError as e:
            log.warning("voice chat turn failed: %s", e)
            await self.push_frame(TextFrame(
                "I lost the KUBERA server mid-thought - "
                f"{type(e).__name__}. Nothing was decided or placed."))
            return
        if body.get("conversation_id") is not None:
            self._conversation_id = body["conversation_id"]
        reply = (body.get("reply") or "").strip()
        if not reply:
            reply = ("The server answered with an empty reply - that is a "
                     "bug worth telling the agents about, not a decision.")
        await self.push_frame(TextFrame(reply))

    async def cleanup(self) -> None:
        await super().cleanup()
        await self._client.aclose()
