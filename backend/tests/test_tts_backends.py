"""T072: tests for make_speaker() TTS backend factory in scripts/talk.py.

All tests use sys.modules patching to avoid real audio hardware, API calls,
and model file downloads. Voice errors must never raise — the loop survives them.
"""

import io
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# numpy is skipped INSIDE the tests that synthesize audio (T072b): a
# module-level importorskip hid the audio-FREE tests (missing-key /
# missing-package / missing-model exits) from CI, where numpy is absent.

# talk.py lives in scripts/ and is not a package — import it by path.
SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"


def _import_talk(extra_mods: dict | None = None):
    """Re-import talk module from disk so each test gets a clean state."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("talk_t072", SCRIPTS_DIR / "talk.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, extra_mods or {}):
        spec.loader.exec_module(mod)
    return mod


def _silent_wav(duration_samples: int = 800, rate: int = 16_000) -> bytes:
    """Return a minimal silent WAV that soundfile can round-trip."""
    np = pytest.importorskip("numpy")
    sf = pytest.importorskip("soundfile")
    samples = np.zeros(duration_samples, dtype=np.float32)
    buf = io.BytesIO()
    sf.write(buf, samples, rate, format="WAV")
    return buf.getvalue()


def _fake_openai_module(wav_bytes: bytes) -> types.ModuleType:
    """Minimal fake openai module whose speech.create() returns wav_bytes."""
    speech_resp = MagicMock()
    speech_resp.read.return_value = wav_bytes
    client_instance = MagicMock()
    client_instance.audio.speech.create.return_value = speech_resp
    mod = types.ModuleType("openai")
    setattr(mod, "OpenAI", MagicMock(return_value=client_instance))
    return mod


def _fake_sd() -> MagicMock:
    sd = MagicMock()
    sd.play = MagicMock()
    sd.wait = MagicMock()
    return sd


# ------------------------------------------------------------------ openai backend

def test_openai_speaker_calls_api_and_plays(monkeypatch):
    """openai backend: API is called with correct params and audio is played."""
    wav = _silent_wav()
    fake_openai = _fake_openai_module(wav)
    fake_sd = _fake_sd()
    played_rates = []
    fake_sd.play = lambda data, rate: played_rates.append(rate)

    monkeypatch.setenv("KUBERA_TTS", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("KUBERA_VOICE", "nova")
    monkeypatch.setenv("KUBERA_OPENAI_TTS_MODEL", "tts-1-hd")

    with patch.dict(sys.modules, {"openai": fake_openai, "sounddevice": fake_sd}):
        mod = _import_talk()
        speaker = mod.make_speaker()
        speaker("hello openai")

    client = fake_openai.OpenAI.return_value
    kw = client.audio.speech.create.call_args.kwargs
    assert kw["model"] == "tts-1-hd"
    assert kw["voice"] == "nova"
    assert kw["input"] == "hello openai"
    assert kw["response_format"] == "wav"
    assert played_rates == [16_000]


def test_openai_speaker_missing_key_exits(monkeypatch):
    monkeypatch.setenv("KUBERA_TTS", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with patch.dict(sys.modules, {}):
        mod = _import_talk()
        with pytest.raises(SystemExit, match="OPENAI_API_KEY"):
            mod.make_speaker()


def test_openai_speaker_missing_package_exits(monkeypatch):
    monkeypatch.setenv("KUBERA_TTS", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    # Setting a module to None in sys.modules causes its import to raise ImportError.
    with patch.dict(sys.modules, {"openai": None}):
        mod = _import_talk()
        with pytest.raises(SystemExit, match="pip install openai"):
            mod.make_speaker()


def test_openai_speaker_playback_error_does_not_raise(monkeypatch):
    """A playback exception is caught and printed — never propagated."""
    wav = _silent_wav()
    fake_openai = _fake_openai_module(wav)
    fake_sd = _fake_sd()
    fake_sd.play = MagicMock(side_effect=RuntimeError("no device"))

    monkeypatch.setenv("KUBERA_TTS", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    with patch.dict(sys.modules, {"openai": fake_openai, "sounddevice": fake_sd}):
        mod = _import_talk()
        speaker = mod.make_speaker()
        speaker("test")  # must not raise


# ------------------------------------------------------------------ kokoro backend

def _fake_kokoro_module() -> tuple[types.ModuleType, MagicMock]:
    """Return (kokoro_onnx module, the Kokoro instance mock)."""
    np = pytest.importorskip("numpy")
    samples = np.zeros(800, dtype=np.float32)
    instance = MagicMock()
    instance.create.return_value = (samples, 24_000)
    klass = MagicMock(return_value=instance)
    mod = types.ModuleType("kokoro_onnx")
    setattr(mod, "Kokoro", klass)
    return mod, instance


def test_kokoro_speaker_calls_create_and_plays(monkeypatch, tmp_path):
    """kokoro backend: Kokoro.create is called and audio is played."""
    kokoro_mod, kokoro_instance = _fake_kokoro_module()
    fake_sd = _fake_sd()
    played_rates = []
    fake_sd.play = lambda data, rate: played_rates.append(rate)

    kokoro_dir = tmp_path / "kokoro"
    kokoro_dir.mkdir()
    (kokoro_dir / "kokoro-v1.0.onnx").write_bytes(b"model")
    (kokoro_dir / "voices-v1.0.bin").write_bytes(b"voices")

    monkeypatch.setenv("KUBERA_TTS", "kokoro")
    monkeypatch.setenv("KUBERA_KOKORO_DIR", str(kokoro_dir))
    monkeypatch.setenv("KUBERA_VOICE", "bf_emma")

    with patch.dict(sys.modules, {"kokoro_onnx": kokoro_mod, "sounddevice": fake_sd}):
        mod = _import_talk()
        speaker = mod.make_speaker()
        speaker("hello kokoro")

    kokoro_instance.create.assert_called_once()
    call_kw = kokoro_instance.create.call_args.kwargs
    assert call_kw.get("voice") == "bf_emma"
    assert call_kw.get("lang") == "en-us"
    assert played_rates == [24_000]


def test_kokoro_missing_models_exits(monkeypatch, tmp_path):
    """kokoro backend: SystemExit with download URL when model files are absent."""
    kokoro_mod, _ = _fake_kokoro_module()
    fake_sd = _fake_sd()
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    monkeypatch.setenv("KUBERA_TTS", "kokoro")
    monkeypatch.setenv("KUBERA_KOKORO_DIR", str(empty_dir))

    with patch.dict(sys.modules, {"kokoro_onnx": kokoro_mod, "sounddevice": fake_sd}):
        mod = _import_talk()
        with pytest.raises(SystemExit, match="kokoro-onnx/releases"):
            mod.make_speaker()


def test_kokoro_missing_package_exits(monkeypatch, tmp_path):
    """kokoro backend: SystemExit when kokoro-onnx is not installed."""
    monkeypatch.setenv("KUBERA_TTS", "kokoro")
    monkeypatch.setenv("KUBERA_KOKORO_DIR", str(tmp_path))

    with patch.dict(sys.modules, {"kokoro_onnx": None}):
        mod = _import_talk()
        with pytest.raises(SystemExit, match="pip install kokoro-onnx"):
            mod.make_speaker()


def test_kokoro_playback_error_does_not_raise(monkeypatch, tmp_path):
    """A kokoro runtime error must not kill the voice loop."""
    kokoro_mod, _ = _fake_kokoro_module()
    fake_sd = _fake_sd()
    fake_sd.play = MagicMock(side_effect=RuntimeError("audio device gone"))

    kokoro_dir = tmp_path / "k"
    kokoro_dir.mkdir()
    (kokoro_dir / "kokoro-v1.0.onnx").write_bytes(b"x")
    (kokoro_dir / "voices-v1.0.bin").write_bytes(b"x")

    monkeypatch.setenv("KUBERA_TTS", "kokoro")
    monkeypatch.setenv("KUBERA_KOKORO_DIR", str(kokoro_dir))

    with patch.dict(sys.modules, {"kokoro_onnx": kokoro_mod, "sounddevice": fake_sd}):
        mod = _import_talk()
        speaker = mod.make_speaker()
        speaker("test")  # must not raise
