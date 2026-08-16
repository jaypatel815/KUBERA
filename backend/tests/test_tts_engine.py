"""T098 — local-first voice for the Orb (D024).

No audio hardware, no model download, no network. Note what is NOT imported at
module scope: numpy and soundfile. The WAV encoder is fed plain Python lists on
purpose — that is the whole point of writing it against the standard library
(I016: an audio import at collection time aborts the entire suite on any machine
that lacks the optional voice deps, which includes CI).
"""

import struct
import sys
import types
import wave
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api import tts_engine
from api.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clean_engine(monkeypatch):
    """Every test starts with no cached model and no inherited env."""
    tts_engine.reset_model_cache()
    monkeypatch.delenv("KUBERA_TTS_SERVER", raising=False)
    monkeypatch.delenv("KUBERA_KOKORO_DIR", raising=False)
    monkeypatch.delenv("KUBERA_VOICE", raising=False)
    yield
    tts_engine.reset_model_cache()


def _model_dir(tmp_path):
    d = tmp_path / "kokoro"
    d.mkdir()
    (d / tts_engine.MODEL_FILE).write_bytes(b"onnx")
    (d / tts_engine.VOICES_FILE).write_bytes(b"voices")
    return d


def _fake_kokoro(samples, rate=24_000):
    instance = MagicMock()
    instance.create.return_value = (samples, rate)
    mod = types.ModuleType("kokoro_onnx")
    setattr(mod, "Kokoro", MagicMock(return_value=instance))
    return mod, instance


# ------------------------------------------------------------- WAV encoding

def test_wav_bytes_are_a_real_parseable_wav():
    wav = tts_engine.pcm16_wav_bytes([0.0, 0.5, -0.5, 1.0], sample_rate=24_000)
    with wave.open(BytesIO(wav), "rb") as r:
        assert r.getnchannels() == 1
        assert r.getsampwidth() == 2
        assert r.getframerate() == 24_000
        assert r.getnframes() == 4


def test_wav_sample_values_are_exact():
    """Hand-computed: 0.5 * 32767 = 16383.5, rounds to 16384; 1.0 -> 32767."""
    wav = tts_engine.pcm16_wav_bytes([0.0, 0.5, -1.0, 1.0])
    with wave.open(BytesIO(wav), "rb") as r:
        frames = r.readframes(r.getnframes())
    assert list(struct.unpack("<4h", frames)) == [0, 16384, -32767, 32767]


def test_wav_clamps_instead_of_wrapping():
    """Out-of-range input must clip, not overflow — a wrap is an audible bang."""
    wav = tts_engine.pcm16_wav_bytes([2.5, -2.5])
    with wave.open(BytesIO(wav), "rb") as r:
        frames = r.readframes(r.getnframes())
    assert list(struct.unpack("<2h", frames)) == [32767, -32767]


def test_wav_accepts_numpy_like_without_importing_numpy():
    """Duck-typed via .tolist() so the encoder never needs numpy installed."""
    class FakeArray:
        def tolist(self):
            return [0.0, 1.0]

    wav = tts_engine.pcm16_wav_bytes(FakeArray())
    with wave.open(BytesIO(wav), "rb") as r:
        assert r.getnframes() == 2


def test_module_does_not_import_audio_libraries_at_collection():
    """The I016 guard, asserted rather than assumed."""
    src = (tts_engine.__file__)
    with open(src, encoding="utf-8") as fh:
        head = fh.read().split("def ")[0]
    assert "import numpy" not in head
    assert "import soundfile" not in head


# ------------------------------------------------------------- backend choice

def test_auto_prefers_local_when_model_present(tmp_path, monkeypatch):
    monkeypatch.setenv("KUBERA_KOKORO_DIR", str(_model_dir(tmp_path)))
    assert tts_engine.resolve_backend() == "kokoro"


def test_auto_falls_back_to_edge_when_model_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("KUBERA_KOKORO_DIR", str(tmp_path / "nothing-here"))
    assert tts_engine.resolve_backend() == "edge"


def test_explicit_choice_wins_over_availability(tmp_path, monkeypatch):
    monkeypatch.setenv("KUBERA_KOKORO_DIR", str(_model_dir(tmp_path)))
    monkeypatch.setenv("KUBERA_TTS_SERVER", "edge")
    assert tts_engine.resolve_backend() == "edge"


def test_unknown_backend_degrades_to_auto_not_an_error(tmp_path, monkeypatch):
    """A typo in an env var must not cost the owner his voice interface."""
    monkeypatch.setenv("KUBERA_KOKORO_DIR", str(_model_dir(tmp_path)))
    monkeypatch.setenv("KUBERA_TTS_SERVER", "kokoroo")
    assert tts_engine.resolve_backend() == "kokoro"


def test_download_hint_names_the_missing_files(tmp_path, monkeypatch):
    d = tmp_path / "empty"
    d.mkdir()
    (d / tts_engine.MODEL_FILE).write_bytes(b"x")  # only one of the two
    monkeypatch.setenv("KUBERA_KOKORO_DIR", str(d))
    hint = tts_engine.download_hint()
    assert tts_engine.VOICES_FILE in hint
    assert tts_engine.MODEL_FILE not in hint.split("missing:")[1].split(".")[0]
    assert "kokoro-onnx/releases" in hint


# ------------------------------------------------------------- local synthesis

def test_synthesize_local_returns_wav_and_passes_voice(tmp_path, monkeypatch):
    d = _model_dir(tmp_path)
    monkeypatch.setenv("KUBERA_KOKORO_DIR", str(d))
    mod, instance = _fake_kokoro([0.0, 0.25, -0.25])

    with patch.dict(sys.modules, {"kokoro_onnx": mod}):
        wav = tts_engine.synthesize_local("you are up 4 percent", voice="bf_emma")

    assert wav[:4] == b"RIFF"
    assert instance.create.call_args.kwargs["voice"] == "bf_emma"


def test_model_is_loaded_once_and_cached(tmp_path, monkeypatch):
    """350 MB of weights must not be re-read on every sentence."""
    monkeypatch.setenv("KUBERA_KOKORO_DIR", str(_model_dir(tmp_path)))
    mod, _ = _fake_kokoro([0.0])

    with patch.dict(sys.modules, {"kokoro_onnx": mod}):
        tts_engine.synthesize_local("one")
        tts_engine.synthesize_local("two")

    assert mod.Kokoro.call_count == 1


def test_missing_model_raises_actionable_error(tmp_path, monkeypatch):
    monkeypatch.setenv("KUBERA_KOKORO_DIR", str(tmp_path / "absent"))
    with pytest.raises(tts_engine.LocalVoiceUnavailable, match="kokoro-onnx/releases"):
        tts_engine.synthesize_local("hello")


def test_missing_package_raises_actionable_error(tmp_path, monkeypatch):
    monkeypatch.setenv("KUBERA_KOKORO_DIR", str(_model_dir(tmp_path)))
    with patch.dict(sys.modules, {"kokoro_onnx": None}):
        with pytest.raises(tts_engine.LocalVoiceUnavailable, match="pip install kokoro-onnx"):
            tts_engine.synthesize_local("hello")


# ------------------------------------------------------------- the endpoint

def test_post_tts_speaks_locally_and_returns_wav(tmp_path, monkeypatch):
    monkeypatch.setenv("KUBERA_KOKORO_DIR", str(_model_dir(tmp_path)))
    mod, instance = _fake_kokoro([0.0, 0.1])

    with patch.dict(sys.modules, {"kokoro_onnx": mod}):
        r = client.post("/api/tts", json={"text": "AAPL is up 2 percent"})

    assert r.status_code == 200
    assert r.headers["content-type"] == "audio/wav"
    assert r.content[:4] == b"RIFF"
    assert instance.create.call_args.args[0] == "AAPL is up 2 percent"


def test_post_tts_rejects_empty_text_before_any_engine_runs():
    r = client.post("/api/tts", json={"text": "   "})
    assert r.status_code == 422


def test_forced_local_without_model_is_503_not_a_silent_cloud_call(tmp_path, monkeypatch):
    """The point of forcing local is privacy. Downgrading quietly would betray it."""
    monkeypatch.setenv("KUBERA_TTS_SERVER", "kokoro")
    monkeypatch.setenv("KUBERA_KOKORO_DIR", str(tmp_path / "absent"))

    r = client.post("/api/tts", json={"text": "hello"})
    assert r.status_code == 503
    assert "kokoro-onnx/releases" in r.json()["detail"]


def test_get_still_works_for_older_clients(tmp_path, monkeypatch):
    """T073's tests and curl keep working; only the Orb moved to POST."""
    monkeypatch.setenv("KUBERA_KOKORO_DIR", str(_model_dir(tmp_path)))
    mod, _ = _fake_kokoro([0.0])

    with patch.dict(sys.modules, {"kokoro_onnx": mod}):
        r = client.get("/api/tts", params={"text": "hello"})

    assert r.status_code == 200
    assert r.content[:4] == b"RIFF"


def test_orb_no_longer_puts_reply_text_in_a_url():
    """Regression guard for the actual leak: text in a GET query string."""
    from pathlib import Path

    orb = Path(tts_engine.__file__).resolve().parents[2] / "apps" / "web" / "orb.html"
    html = orb.read_text(encoding="utf-8")
    assert "/api/tts?text=" not in html
    assert '"/api/tts"' in html
