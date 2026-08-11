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


def test_nonnegotiable_keywords_present():
    """The rules that make KUBERA trustworthy, by keyword — belt and suspenders."""
    prompt = build_system_prompt("t", []).lower()
    for keyword in (
        "tool call", "recency", "asof", "never present an outcome as certain",
        "backtests describe the past", "paper account", "explicit confirmation",
        "risk engine", "never fill gaps", "not a licensed financial advisor",
    ):
        assert keyword in prompt, f"missing persona keyword: {keyword}"
