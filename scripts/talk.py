"""Talk to KUBERA (T070): push-to-talk voice loop for the desktop.

Usage (server must be running: uvicorn --app-dir backend api.main:app):
    python scripts/talk.py                # Enter = start recording, Enter again = stop
    python scripts/talk.py --url http://127.0.0.1:8000

At the prompt:
    [Enter]          record a question (Enter again stops recording)
    confirm          record a CONFIRMED turn (sets confirm=true — deliberate, typed)
    q                quit

Dependencies (see requirements-voice.txt):  pip install -r requirements-voice.txt
STT backends (env KUBERA_STT):  whisper (local, default)  |  openai (needs OPENAI_API_KEY)

Voice quality ladder (env KUBERA_TTS) — set KUBERA_VOICE to override the default voice:
  sapi      Windows built-in (default, robotic — works with zero deps)
  edge      Microsoft neural voices via edge-tts (big quality jump, free, online)
              pip install edge-tts soundfile
              KUBERA_VOICE=en-US-AndrewNeural  (most natural; GuyNeural is default)
  openai    OpenAI TTS API (near-human, ~$0.015/1k chars, OPENAI_API_KEY required)
              pip install openai soundfile
              KUBERA_VOICE=alloy  (also: echo, fable, onyx, nova, shimmer)
              KUBERA_OPENAI_TTS_MODEL=tts-1  (or tts-1-hd for highest quality)
  kokoro    Local near-human via kokoro-onnx (free, offline, 50+ voices, ~350 MB)
              pip install kokoro-onnx soundfile
              Needs kokoro-v1.0.onnx + voices-v1.0.bin in KUBERA_KOKORO_DIR
              (download from https://github.com/thewh1teagle/kokoro-onnx/releases)
              KUBERA_VOICE=af_heart  (also: af_sarah, am_adam, bf_emma, bm_george, …)

Safety (D015): speech never confirms an order. Only typing `confirm` sets the flag.
"""

import argparse
import io
import os
import sys
import wave
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

import httpx  # noqa: E402

from api.voice_loop import VoiceState, run_voice_turn  # noqa: E402

SAMPLE_RATE = 16_000


# ----------------------------------------------------------------- audio in

def record_push_to_talk() -> bytes:
    try:
        import numpy as np  # noqa: PLC0415
        import sounddevice as sd  # noqa: PLC0415
    except ImportError:
        raise SystemExit("Missing audio deps — run: pip install -r requirements-voice.txt")

    print("  recording... press Enter to stop")
    chunks = []
    stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16",
                            callback=lambda data, *_: chunks.append(data.copy()))
    with stream:
        input()
    if not chunks:
        return b""
    audio = np.concatenate(chunks)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(audio.tobytes())
    return buf.getvalue()


# ----------------------------------------------------------------- STT

def make_transcriber():
    backend = os.environ.get("KUBERA_STT", "whisper").lower()
    if backend == "openai":
        key = os.environ.get("OPENAI_API_KEY", "")
        if not key:
            raise SystemExit("KUBERA_STT=openai needs OPENAI_API_KEY in the environment.")

        def openai_stt(audio: bytes) -> str:
            r = httpx.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {key}"},
                files={"file": ("speech.wav", audio, "audio/wav")},
                data={"model": "whisper-1"},
                timeout=60,
            )
            r.raise_for_status()
            return r.json().get("text", "")

        return openai_stt

    try:
        from faster_whisper import WhisperModel  # noqa: PLC0415
    except ImportError:
        raise SystemExit(
            "Local STT needs faster-whisper (pip install faster-whisper). If wheels "
            "aren't available for your Python, set KUBERA_STT=openai instead."
        )
    print("loading local Whisper model (first run downloads it)...")
    model = WhisperModel("small", device="cpu", compute_type="int8")

    def whisper_stt(audio: bytes) -> str:
        segments, _info = model.transcribe(io.BytesIO(audio), language="en")
        return " ".join(s.text for s in segments)

    return whisper_stt


# ----------------------------------------------------------------- TTS

def make_speaker():
    """Factory: return a speak(text: str) -> None callable based on KUBERA_TTS.

    Backends: sapi (default) | edge | openai | kokoro
    Voice is controlled by KUBERA_VOICE; each backend documents its default above.
    Voice errors are printed but NEVER raise — the text reply is always shown.
    """
    backend = os.environ.get("KUBERA_TTS", "sapi").lower()

    # ---- edge: Microsoft neural voices (free, online, needs edge-tts + soundfile) ----
    if backend == "edge":
        try:
            import asyncio  # noqa: PLC0415

            import edge_tts  # noqa: PLC0415
            import sounddevice as sd  # noqa: PLC0415
            import soundfile as sf  # noqa: PLC0415
        except ImportError:
            raise SystemExit("KUBERA_TTS=edge needs: pip install edge-tts soundfile")

        # Pick a voice with KUBERA_VOICE (try en-US-AndrewNeural — very natural).
        voice = os.environ.get("KUBERA_VOICE", "en-US-GuyNeural")

        def edge_speak(text: str) -> None:
            async def synth() -> bytes:
                out = io.BytesIO()
                communicate = edge_tts.Communicate(text, voice)
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        out.write(chunk["data"])
                return out.getvalue()

            try:
                data, rate = sf.read(io.BytesIO(asyncio.run(synth())))
                sd.play(data, rate)
                sd.wait()
            except Exception as e:  # voice must never kill the loop; text still prints
                print(f"  [voice playback failed: {e}]")

        return edge_speak

    # ---- openai: OpenAI TTS API (near-human, pennies, needs OPENAI_API_KEY) ----
    if backend == "openai":
        key = os.environ.get("OPENAI_API_KEY", "")
        if not key:
            raise SystemExit(
                "KUBERA_TTS=openai needs OPENAI_API_KEY in the environment.\n"
                "Alternatively, set KUBERA_TTS=edge (free) or KUBERA_TTS=kokoro (offline)."
            )
        try:
            import openai as _openai  # noqa: PLC0415
            import sounddevice as sd  # noqa: PLC0415
            import soundfile as sf  # noqa: PLC0415
        except ImportError:
            raise SystemExit(
                "KUBERA_TTS=openai needs: pip install openai soundfile\n"
                "sounddevice should already be installed from requirements-voice.txt."
            )

        voice = os.environ.get("KUBERA_VOICE", "alloy")
        model = os.environ.get("KUBERA_OPENAI_TTS_MODEL", "tts-1")
        client = _openai.OpenAI(api_key=key)

        def openai_speak(text: str) -> None:
            try:
                response = client.audio.speech.create(
                    model=model,
                    voice=voice,  # type: ignore[arg-type]
                    input=text,
                    response_format="wav",  # wav avoids mp3 decode dependency
                )
                audio_bytes = response.read()
                data, rate = sf.read(io.BytesIO(audio_bytes))
                sd.play(data, rate)
                sd.wait()
            except Exception as e:  # voice must never kill the loop; text still prints
                print(f"  [voice playback failed: {e}]")

        return openai_speak

    # ---- kokoro: local near-human TTS via kokoro-onnx (free, offline, 50+ voices) ----
    if backend == "kokoro":
        try:
            import sounddevice as sd  # noqa: PLC0415
            from kokoro_onnx import Kokoro  # noqa: PLC0415
        except ImportError:
            raise SystemExit(
                "KUBERA_TTS=kokoro needs: pip install kokoro-onnx soundfile\n"
                "sounddevice should already be installed from requirements-voice.txt."
            )

        kokoro_dir = Path(
            os.environ.get("KUBERA_KOKORO_DIR", Path(__file__).parent.parent / "models" / "kokoro")
        )
        model_path  = kokoro_dir / "kokoro-v1.0.onnx"
        voices_path = kokoro_dir / "voices-v1.0.bin"
        if not model_path.exists() or not voices_path.exists():
            raise SystemExit(
                f"KUBERA_TTS=kokoro: model files not found in {kokoro_dir}\n"
                "Download kokoro-v1.0.onnx and voices-v1.0.bin from:\n"
                "  https://github.com/thewh1teagle/kokoro-onnx/releases\n"
                "Then either place them in that directory or set KUBERA_KOKORO_DIR "
                "to the folder that contains them."
            )

        print("loading kokoro model (first run may take a few seconds)...")
        voice = os.environ.get("KUBERA_VOICE", "af_heart")
        koko = Kokoro(str(model_path), str(voices_path))

        def kokoro_speak(text: str) -> None:
            try:
                samples, sample_rate = koko.create(text, voice=voice, speed=1.0, lang="en-us")
                sd.play(samples, sample_rate)
                sd.wait()
            except Exception as e:  # voice must never kill the loop; text still prints
                print(f"  [voice playback failed: {e}]")

        return kokoro_speak

    # ---- sapi: Windows built-in TTS (default, no extra deps) ----
    try:
        import pyttsx3  # noqa: PLC0415
    except ImportError:
        raise SystemExit("TTS needs pyttsx3 — run: pip install -r requirements-voice.txt")

    def sapi_speak(text: str) -> None:
        # pyttsx3's runAndWait() speaks exactly once per engine on Windows (known bug:
        # later calls are silently ignored). A fresh engine per utterance fixes it.
        # See ISSUES.md I006.
        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", 185)
            engine.say(text)
            engine.runAndWait()
            engine.stop()
        except Exception as e:  # voice must never kill the loop; text still prints
            print(f"  [voice playback failed: {e}]")

    return sapi_speak


# ----------------------------------------------------------------- main

def main() -> int:
    parser = argparse.ArgumentParser(description="Talk to KUBERA (push-to-talk)")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    transcriber = make_transcriber()
    speaker = make_speaker()
    state = VoiceState()

    def chat_fn(text: str, conversation_id: int | None, confirm: bool) -> dict:
        try:
            r = httpx.post(
                f"{args.url}/api/chat",
                json={"message": text, "conversation_id": conversation_id,
                      "voice": True, "confirm": confirm},
                timeout=180,
            )
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as e:
            try:
                detail = e.response.json().get("detail", e.response.text)
            except Exception:
                detail = e.response.text
            raise SystemExit(f"\nServer error ({e.response.status_code}): {detail}\n") from e

    print("\nKUBERA voice loop — Enter or 'v' to talk, 'confirm' for a confirmed turn, "
          "'q' to quit.")
    while True:
        cmd = input("\n[Enter/v]=talk  confirm  q > ").strip().lower()
        if cmd == "q":
            print("bye")
            return 0
        if cmd in ("", "v"):
            confirm = False
        elif cmd == "confirm":
            confirm = True
        else:
            print(f"Unknown input '{cmd}'. Press Enter or 'v' to talk, 'confirm' for a "
                  "confirmed turn, 'q' to quit.")
            continue
        audio = record_push_to_talk()
        report = run_voice_turn(audio, transcriber, chat_fn, speaker, state,
                                confirm=confirm)
        if report["heard"]:
            print(f"  you: {report['heard']}")
        print(f"  kubera: {report['reply']}")


if __name__ == "__main__":
    sys.exit(main())
