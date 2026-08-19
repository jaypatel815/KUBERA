# Realtime voice for KUBERA — framework research (T074a)

Date: 2026-08-19. Author: Claude/Cowork. Method: web research (sources at
the bottom); NO code built from this doc alone — the framework choice gets
a spike ticket whose probe observes the real thing (D030), same as FMP and
EDGAR did.

## The question

KUBERA's voice today is push-to-talk (T070) with local TTS (D024: kokoro,
pyttsx3 fallback) narrated through the Orb (T073). T074 asks: can the
owner TALK with KUBERA — full duplex, interruptible, sub-second — without
abandoning D024 (local-first) or the architecture rule that every reply
passes through OUR chat layer (persona, tool registry, safety rails,
recency post-check)? Three candidate stacks were current in August 2026:
LiveKit Agents, Pipecat, and OpenAI's Realtime API.

## What the research found

**OpenAI Realtime API** (speech-to-speech): gpt-realtime-2.1 bills $32 per
million audio-input tokens and $64 per million audio-output tokens —
measured real-world cost $0.18–0.46/min uncached, $0.05–0.10/min with
prompt caching; the mini model is ~60% cheaper. But price is not the
disqualifier. A speech-to-speech model IS the brain: adopting it would
route trades-talk through OpenAI's model, not through KUBERA's persona,
tool subsetting, confirmation gates, and rails. That violates the
architecture, not the budget. DISPOSITION: not a candidate. Recorded here
as the paid comparison point under D034 in case the owner ever wants a
cloud fallback mode.

**Anthropic native voice**: as of August 2026 there is no Claude
speech-to-speech API. Claude Code's voice mode (rolled out from March
2026) is dictation — STT into the prompt box, free, claude.ai-auth only,
explicitly NOT available via API key. Claude app voice mode is a product
feature, not an API. DISPOSITION: nothing to build on first-party;
re-check at T074 build time.

**LiveKit Agents** (Apache-2.0, ~11k stars, the most-adopted OSS voice
runtime of 2026): agent joins a LiveKit *room* as a participant — the
design center is multi-user WebRTC through a media server. Self-hosting
the full stack is documented at weeks of infra work to reach parity with
their cloud. KUBERA is ONE user on ONE desktop talking to a local server.
DISPOSITION: capable but wrong-shaped; the media-server tax buys nothing
here.

**Pipecat** (BSD-2, maintained by Daily): a pipeline framework — VAD →
STT → LLM → TTS as swappable processors — that matches KUBERA's existing
pieces almost embarrassingly well:

- `KokoroTTSService` is a DOCUMENTED Pipecat service, on-device, no keys —
  D024's chosen voice drops in as-is.
- `LocalAudioTransport` does mic+speaker via PyAudio with NO server of any
  kind; `SmallWebRTCTransport` is serverless peer-to-peer WebRTC (no
  external infrastructure) if the Orb browser UI should carry the audio.
- Fully-local stacks are proven in the wild in 2026: whisper.cpp or
  Parakeet STT + Ollama + Kokoro reaching sub-second round trips on
  consumer hardware; Silero VAD for interruption. $0/min.
- LLM-agnostic (Anthropic among 20+ integrations) — but see the catch.

**The catch that makes T074b a real spike, not an install**: Pipecat's LLM
step expects a streaming LLM service. KUBERA's brain is NOT a raw LLM —
it is /api/chat (context assembly, tool loop, rails). The spike's core
question is a custom Pipecat processor that calls OUR chat endpoint and
streams the reply into TTS, so voice-KUBERA and text-KUBERA are the SAME
KUBERA. If that processor fights the framework, the fallback is using
Pipecat only for the audio half (VAD/STT/interruption) and keeping our
own loop — measured, not assumed.

## Disposition

Adopt **Pipecat** as T074's framework, pending the T074b spike. Latency
target from the wild: sub-second is achievable locally; the spike measures
OURS. Keep push-to-talk as the fallback mode permanently (it already
works, and quiet-room dictation beats VAD misfires).

Seeded sub-tickets (added to TASKS.md backlog):
- **T074b** — Pipecat spike: LocalAudioTransport + faster-whisper (or
  whisper.cpp) STT + custom /api/chat processor + existing kokoro TTS.
  Probe-first: measure round-trip latency, interruption behavior, and
  whether the chat-endpoint processor streams cleanly. Exit criterion: a
  recorded conversation with KUBERA's OWN persona answering, or a written
  finding that the processor fights the framework (then the audio-half
  fallback gets its own ticket).
- **T074c** — only after T074b: VAD/interruption tuning + latency
  measurement vs push-to-talk, and the mode switch in the Orb
  (SmallWebRTCTransport if browser audio wins over PyAudio).

D034 note: the local stack is $0/min. If the owner ever wants a cloud
mode, OpenAI Realtime's measured $0.05–0.46/min is the reference price —
but it would sit OUTSIDE the rails and is not recommended for anything
involving positions or orders.

## Sources

- [LiveKit Agents overview + self-hosting reality](https://www.forasoft.com/blog/article/livekit-ai-agents-guide)
- [LiveKit voice agents](https://livekit.com/voice-agents)
- [LiveKit Agents 2026 adoption](https://www.cekura.ai/blogs/livekit-agents)
- [Pipecat GitHub](https://github.com/pipecat-ai/pipecat)
- [Pipecat overview](https://docs.pipecat.ai/overview/pipecat)
- [Pipecat Kokoro TTS service](https://docs.pipecat.ai/api-reference/server/services/tts/kokoro)
- [Pipecat LocalAudioTransport](https://reference-server.pipecat.ai/en/latest/_modules/pipecat/transports/local/audio.html)
- [SmallWebRTCTransport — serverless WebRTC](https://www.daily.co/blog/you-dont-need-a-webrtc-server-for-your-voice-agents/)
- [Local macOS Pipecat agents (kwindla)](https://github.com/kwindla/macos-local-voice-agents)
- [Local stack: Whisper + Ollama + Kokoro](https://everylocalai.com/stack/local-voice-assistant)
- [OpenAI Realtime pricing math 2026](https://www.layer3labs.io/guides/openai-realtime-api-pricing)
- [Realtime measured sessions (HackerNoon)](https://hackernoon.com/openai-realtime-api-pricing-in-2026-real-world-data-from-4000-measured-sessions)
- [Claude Code voice mode (TechCrunch)](https://techcrunch.com/2026/03/03/claude-code-rolls-out-a-voice-mode-capability/)
- [Claude Code voice dictation docs](https://code.claude.com/docs/en/voice-dictation)
