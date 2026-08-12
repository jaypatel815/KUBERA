"""Voice-loop orchestration — all fakes, no audio hardware."""

from api.voice_loop import HEARD_NOTHING, VoiceState, run_voice_turn


class FakeChat:
    def __init__(self):
        self.calls = []

    def __call__(self, text, conversation_id, confirm):
        self.calls.append({"text": text, "conversation_id": conversation_id,
                           "confirm": confirm})
        return {"conversation_id": 7, "reply": f"You said: {text}",
                "tool_calls": [{"name": "get_portfolio", "arguments": {}}]}


class FakeSpeaker:
    def __init__(self):
        self.spoken = []

    def __call__(self, text):
        self.spoken.append(text)


def test_full_turn_transcribes_chats_and_speaks():
    chat, speaker = FakeChat(), FakeSpeaker()
    state = VoiceState()
    report = run_voice_turn(b"AUDIO", lambda a: "how is my portfolio",
                            chat, speaker, state)
    assert report["chat_called"] is True
    assert chat.calls[0]["text"] == "how is my portfolio"
    assert speaker.spoken == ["You said: how is my portfolio"]
    assert state.conversation_id == 7 and state.turns == 1


def test_conversation_threads_across_turns():
    chat, speaker = FakeChat(), FakeSpeaker()
    state = VoiceState()
    run_voice_turn(b"A", lambda a: "first", chat, speaker, state)
    run_voice_turn(b"B", lambda a: "second", chat, speaker, state)
    assert chat.calls[0]["conversation_id"] is None  # new conversation
    assert chat.calls[1]["conversation_id"] == 7  # threaded
    assert state.turns == 2


def test_silence_never_reaches_kubera():
    chat, speaker = FakeChat(), FakeSpeaker()
    report = run_voice_turn(b"", lambda a: "   ", chat, speaker, VoiceState())
    assert report["chat_called"] is False
    assert chat.calls == []
    assert speaker.spoken == [HEARD_NOTHING]


def test_confirm_gesture_passes_through_only_when_set():
    chat, speaker = FakeChat(), FakeSpeaker()
    state = VoiceState()
    run_voice_turn(b"A", lambda a: "buy it", chat, speaker, state)
    run_voice_turn(b"B", lambda a: "yes do it", chat, speaker, state, confirm=True)
    assert chat.calls[0]["confirm"] is False  # spoken words alone never confirm
    assert chat.calls[1]["confirm"] is True   # typed gesture did
