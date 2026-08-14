"""Orb UI route + /api/tts (T073) — fake edge_tts, no audio hardware."""

import sys
import types

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_root_serves_orb_page():
    r = client.get("/")
    assert r.status_code == 200
    assert "KUBERA" in r.text
    assert "orb" in r.text.lower()
    assert "confirm this turn" in r.text  # the deliberate-gesture UI is present
    # patience (owner feedback): pauses don't end the turn; silence timer + send-now
    assert "SILENCE_SEND_MS" in r.text
    assert "pauses are fine" in r.text
    assert "continuous = true" in r.text


def test_tts_503_without_edge_tts(monkeypatch):
    monkeypatch.setitem(sys.modules, "edge_tts", None)
    r = client.get("/api/tts", params={"text": "hello"})
    assert r.status_code == 503
    assert "pip install edge-tts" in r.json()["detail"]


def test_tts_streams_audio_with_fake_edge(monkeypatch):
    mod = types.ModuleType("edge_tts")

    class Communicate:
        def __init__(self, text, voice):
            mod.captured = {"text": text, "voice": voice}

        async def stream(self):
            yield {"type": "audio", "data": b"MP3A"}
            yield {"type": "WordBoundary"}  # non-audio chunks are skipped
            yield {"type": "audio", "data": b"MP3B"}

    mod.Communicate = Communicate
    monkeypatch.setitem(sys.modules, "edge_tts", mod)

    r = client.get("/api/tts", params={"text": "hello there", "voice": "en-US-AriaNeural"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("audio/mpeg")
    assert r.content == b"MP3AMP3B"
    assert mod.captured == {"text": "hello there", "voice": "en-US-AriaNeural"}


def test_tts_rejects_empty_text(monkeypatch):
    mod = types.ModuleType("edge_tts")
    mod.Communicate = object
    monkeypatch.setitem(sys.modules, "edge_tts", mod)
    r = client.get("/api/tts", params={"text": "   "})
    assert r.status_code == 422
