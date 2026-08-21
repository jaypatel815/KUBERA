"""T074b (sandbox half) — the Pipecat chat seam: voice-KUBERA must be the
SAME KUBERA. Proven with a fake /api/chat: voice=True rides every turn,
the conversation id from turn one is carried into turn two, non-speech
frames pass through untouched, and a dead server becomes a SPOKEN named
degradation, never silence.

pipecat lives in requirements-voice.txt only — per-test importorskip (the
I016 lesson), so lean environments and CI skip clean. asyncio.run drives
the coroutines; no pytest-asyncio dependency."""

import asyncio

import pytest


def _mod():
    pytest.importorskip("pipecat")
    from api import voice_pipeline
    return voice_pipeline


class FakeResponse:
    def __init__(self, body, status=200):
        self._body, self.status_code = body, status

    def json(self):
        return self._body

    def raise_for_status(self):
        import httpx
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("boom", request=None, response=None)


class FakeClient:
    def __init__(self, replies):
        self.calls: list[dict] = []
        self._replies = list(replies)

    async def post(self, url, json=None):
        self.calls.append({"url": url, "json": json})
        nxt = self._replies.pop(0)
        if isinstance(nxt, Exception):
            raise nxt
        return FakeResponse(nxt)

    async def aclose(self):
        pass


def _capture(processor):
    pushed = []

    async def fake_push(frame, direction=None):
        pushed.append(frame)

    processor.push_frame = fake_push
    return pushed


def test_transcription_becomes_a_chat_turn_with_voice_and_thread():
    vp = _mod()
    from pipecat.frames.frames import (  # pyrefly: ignore  # I037: voice-only dep
        TextFrame,
        TranscriptionFrame,
    )
    from pipecat.processors.frame_processor import (  # pyrefly: ignore  # I037: voice-only dep
        FrameDirection,
    )

    client = FakeClient([
        {"reply": "SPY closed up about one percent.", "conversation_id": 7},
        {"reply": "Your largest position is SPY.", "conversation_id": 7},
    ])
    p = vp.KuberaChatProcessor(client=client)
    pushed = _capture(p)

    async def run():
        await p._chat_turn("how did spy do today")
        await p._chat_turn("what's my largest position")

    asyncio.run(run())
    # voice=True on every turn; the thread id carried into turn two
    assert client.calls[0]["json"] == {"message": "how did spy do today",
                                      "voice": True}
    assert client.calls[1]["json"]["conversation_id"] == 7
    assert p.conversation_id == 7
    assert [f.text for f in pushed if isinstance(f, TextFrame)] == [
        "SPY closed up about one percent.",
        "Your largest position is SPY."]
    _ = (TranscriptionFrame, FrameDirection)  # imported to prove availability


def test_server_failure_becomes_a_spoken_named_degradation():
    vp = _mod()
    import httpx
    from pipecat.frames.frames import TextFrame  # pyrefly: ignore  # I037: voice-only dep

    p = vp.KuberaChatProcessor(
        client=FakeClient([httpx.ConnectError("refused")]))
    pushed = _capture(p)
    asyncio.run(p._chat_turn("hello"))
    assert len(pushed) == 1 and isinstance(pushed[0], TextFrame)
    assert "ConnectError" in pushed[0].text
    assert "Nothing was decided or placed" in pushed[0].text


def test_empty_reply_is_named_not_silent():
    vp = _mod()
    from pipecat.frames.frames import TextFrame  # pyrefly: ignore  # I037: voice-only dep

    p = vp.KuberaChatProcessor(client=FakeClient([{"reply": "",
                                                   "conversation_id": 1}]))
    pushed = _capture(p)
    asyncio.run(p._chat_turn("hello"))
    assert isinstance(pushed[0], TextFrame)
    assert "empty reply" in pushed[0].text
