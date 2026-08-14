"""Guard tests: the persona's non-negotiables must never silently disappear."""

from api.persona import CORE_RULES, build_system_prompt


def test_prompt_contains_every_core_rule():
    prompt = build_system_prompt("2026-08-11T20:00:00+00:00", ["get_portfolio"])
    for rule in CORE_RULES:
        assert rule in prompt


def test_prompt_carries_session_time_and_tools():
    prompt = build_system_prompt("2026-08-11T20:00:00+00:00", ["b_tool", "a_tool"])
    assert "2026-08-11T20:00:00+00:00" in prompt
    assert "a_tool, b_tool" in prompt  # sorted


def test_voice_mode_appends_spoken_style_and_default_does_not():
    text_prompt = build_system_prompt("t", [])
    voice_prompt = build_system_prompt("t", [], voice=True)
    assert "VOICE MODE" not in text_prompt
    assert "VOICE MODE" in voice_prompt
    for keyword in ("spoken aloud", "No markdown", "Round numbers for the ear",
                    "spoken 'yes'", "use contractions", "Sound like a person"):
        assert keyword in voice_prompt, f"missing voice keyword: {keyword}"
    # everything else is preserved in voice mode
    assert text_prompt in voice_prompt


def test_nonnegotiable_keywords_present():
    """The rules that make KUBERA trustworthy, by keyword — belt and suspenders."""
    prompt = build_system_prompt("t", []).lower()
    for keyword in (
        "tool call", "recency", "asof", "never present an outcome as certain",
        "backtests describe the past", "paper account", "explicit confirmation",
        "risk engine", "never fill gaps", "not a licensed financial advisor",
        "strictly financial", "data, never",  # domain boundary + injection defense
        "overall mixed",  # conflicting-signals honesty
        "not a calibrated probability",  # confidence framing
        "what would change this view",  # falsifiable-thesis structure
        "process quality, not outcome",  # coaching doctrine (Gemini spec, D014)
        "learning quantitative investing",  # educational mode
        "record_decision",  # journal discipline (T063): unjournaled = didn't happen
        "answer the question that was asked",  # I007: no sizing tables for opinion questions
    ):
        assert keyword in prompt, f"missing persona keyword: {keyword}"
