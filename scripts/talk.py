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
TTS backends (env KUBERA_TTS):  sapi (Windows built-in, default)  |  edge (neural voices)

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
    backend = os.environ.get("KUBERA_TTS", "sapi").lower()
    if backend == "edge":
        try:
            import asyncio  # noqa: PLC0415

            import edge_tts  # noqa: PLC0415
            import sounddevice as sd  # noqa: PLC0415
            import soundfile as sf  # noqa: PLC0415
        except ImportError:
            raise SystemExit("KUBERA_TTS=edge needs: pip install edge-tts soundfile")

        def edge_speak(text: str) -> None:
            async def synth() -> bytes:
                out = io.BytesIO()
                communicate = edge_tts.Communicate(text, "en-US-GuyNeural")
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        out.write(chunk["data"])
                return out.getvalue()

            data, rate = sf.read(io.BytesIO(asyncio.run(synth())))
            sd.play(data, rate)
            sd.wait()

        return edge_speak

    try:
        import pyttsx3  # noqa: PLC0415
    except ImportError:
        raise SystemExit("TTS needs pyttsx3 — run: pip install -r requirements-voice.txt")
    engine = pyttsx3.init()
    engine.setProperty("rate", 185)

    def sapi_speak(text: str) -> None:
        engine.say(text)
        engine.runAndWait()

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
        r = httpx.post(
            f"{args.url}/api/chat",
            json={"message": text, "conversation_id": conversation_id,
                  "voice": True, "confirm": confirm},
            timeout=180,
        )
        r.raise_for_status()
        return r.json()

    print("\nKUBERA voice loop — Enter or 'v' to talk, 'confirm' for a confirmed turn, 'q' to quit.")
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
            print(f"Unknown input '{cmd}'. Press Enter or 'v' to talk, 'confirm' for a confirmed turn, 'q' to quit.")
            continue
        audio = record_push_to_talk()
        report = run_voice_turn(audio, transcriber, chat_fn, speaker, state,
                                confirm=confirm)
        if report["heard"]:
            print(f"  you: {report['heard']}")
        print(f"  kubera: {report['reply']}")


if __name__ == "__main__":
    sys.exit(main())
