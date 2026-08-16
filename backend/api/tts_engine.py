"""T098 — local-first speech for the Orb (D024).

Why this module exists, in one sentence: KUBERA reads the owner's positions and
dollar P&L out loud, so routing that text through a cloud voice service means his
holdings leave the machine on every single reply.

The Orb previously called edge-tts (Microsoft) unconditionally, and did it over a
GET query string — which writes the same sentences into server access logs and
browser history before they ever reach the network. This module gives the server
a local engine and prefers it whenever its model files are present. The cloud
path still works, because a fresh clone with no model downloaded should still
speak, but it is now a deliberate fallback that says so in the log.

Backends (env `KUBERA_TTS_SERVER`):
  auto    (default) local if the kokoro model files are present, else edge
  kokoro  force local; raises LocalVoiceUnavailable if the model is missing
  edge    force cloud (Microsoft neural voices, online)

Deliberate dependency notes:
  * WAV encoding here is pure standard library (`wave` + `struct`). No soundfile,
    no numpy import at module scope. That is not an accident — the sibling voice
    tests broke the entire suite twice by importing audio libraries at collection
    time (I016), and CI installs only backend/requirements.txt.
  * kokoro-onnx is imported lazily, inside the call, for the same reason.
"""

from __future__ import annotations

import logging
import os
import struct
import wave
from io import BytesIO
from pathlib import Path
from typing import Any

log = logging.getLogger("kubera.tts")

# Kokoro's own sample rate. Kept as a constant so a caller can build a WAV header
# without loading the model just to ask.
KOKORO_SAMPLE_RATE = 24_000
DEFAULT_LOCAL_VOICE = "af_heart"
DEFAULT_CLOUD_VOICE = "en-US-AndrewNeural"

MODEL_FILE = "kokoro-v1.0.onnx"
VOICES_FILE = "voices-v1.0.bin"

# Any, not object: kokoro's class cannot be imported for a real annotation (the
# package is optional by design), and `object` makes every attribute access on
# the cached model a type error.
_MODEL_CACHE: Any = None


class LocalVoiceUnavailable(RuntimeError):
    """Raised when the local engine was required but cannot run.

    Carries an actionable message: which file is missing and where to get it.
    """


def kokoro_model_dir() -> Path:
    """Where the local voice model lives — `KUBERA_KOKORO_DIR` or `models/kokoro/`.

    `.resolve()` matters: without it, launching the server through a symlink or a
    relative path computes the wrong directory and the model reports as missing.
    """
    env = os.environ.get("KUBERA_KOKORO_DIR", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return (Path(__file__).resolve().parents[2] / "models" / "kokoro").resolve()


def missing_model_files(directory: Path | None = None) -> list[str]:
    """Return the names of the model files that are absent (empty list = ready)."""
    d = directory or kokoro_model_dir()
    return [name for name in (MODEL_FILE, VOICES_FILE) if not (d / name).exists()]


def local_voice_available(directory: Path | None = None) -> bool:
    return not missing_model_files(directory)


def download_hint(directory: Path | None = None) -> str:
    d = directory or kokoro_model_dir()
    missing = ", ".join(missing_model_files(d)) or "(none)"
    return (
        f"Local voice model not found in {d} — missing: {missing}. "
        f"Download {MODEL_FILE} and {VOICES_FILE} from "
        "https://github.com/thewh1teagle/kokoro-onnx/releases and put them in "
        "that folder (or set KUBERA_KOKORO_DIR to wherever you keep them). "
        "Until then the Orb speaks through the online voice, which means reply "
        "text leaves this machine."
    )


def resolve_backend(explicit: str | None = None, directory: Path | None = None) -> str:
    """Decide which engine speaks. Returns "kokoro" or "edge".

    `auto` is the honest default for a personal tool: use the private engine the
    moment it is possible, without making a fresh clone mute until someone reads
    the docs. An unknown value degrades to auto rather than killing the request —
    a typo in an env var should not cost the owner his voice interface.
    """
    choice = (explicit or os.environ.get("KUBERA_TTS_SERVER") or "auto").strip().lower()
    if choice not in {"auto", "kokoro", "edge"}:
        log.warning("KUBERA_TTS_SERVER=%r is not auto|kokoro|edge — treating as auto", choice)
        choice = "auto"
    if choice == "auto":
        return "kokoro" if local_voice_available(directory) else "edge"
    return choice


# --------------------------------------------------------------- WAV encoding

def pcm16_wav_bytes(samples, sample_rate: int = KOKORO_SAMPLE_RATE) -> bytes:
    """Encode float samples in [-1.0, 1.0] as a 16-bit mono WAV.

    Accepts a numpy array or any plain sequence of floats — numpy is never
    imported here, it is only duck-typed via `.tolist()`. Values outside the
    range are clamped rather than allowed to wrap, because integer overflow in
    audio is not a quiet failure: it is a loud click in the owner's ear.
    """
    seq = samples.tolist() if hasattr(samples, "tolist") else list(samples)
    frames = bytearray()
    for value in seq:
        v = float(value)
        if v > 1.0:
            v = 1.0
        elif v < -1.0:
            v = -1.0
        frames += struct.pack("<h", int(round(v * 32767.0)))

    buf = BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(int(sample_rate))
        w.writeframes(bytes(frames))
    return buf.getvalue()


# --------------------------------------------------------------- local engine

def _load_model(directory: Path | None = None):
    """Load kokoro once and keep it — the model is ~350 MB and slow to warm."""
    global _MODEL_CACHE
    if _MODEL_CACHE is not None:
        return _MODEL_CACHE

    d = directory or kokoro_model_dir()
    if missing_model_files(d):
        raise LocalVoiceUnavailable(download_hint(d))

    try:
        from kokoro_onnx import Kokoro  # noqa: PLC0415 — optional, lazy on purpose
    except ImportError as exc:
        raise LocalVoiceUnavailable(
            "Local voice needs kokoro-onnx in the SERVER venv: pip install kokoro-onnx"
        ) from exc

    log.info("loading local voice model from %s (first call is slow)", d)
    _MODEL_CACHE = Kokoro(str(d / MODEL_FILE), str(d / VOICES_FILE))
    return _MODEL_CACHE


def reset_model_cache() -> None:
    """Drop the cached model. Tests use this; so does a model swap at runtime."""
    global _MODEL_CACHE
    _MODEL_CACHE = None


def synthesize_local(text: str, voice: str | None = None, directory: Path | None = None) -> bytes:
    """Speak `text` locally and return WAV bytes. Nothing leaves the machine."""
    model = _load_model(directory)
    chosen = (voice or os.environ.get("KUBERA_VOICE") or DEFAULT_LOCAL_VOICE).strip()
    samples, rate = model.create(text, voice=chosen, speed=1.0, lang="en-us")
    return pcm16_wav_bytes(samples, rate)
