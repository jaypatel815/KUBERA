"""Per-brain tool subsetting (T096, from I008) — don't hand a 31-tool menu to a
model that can't hold it.

Two live routing failures came from a small local model drowning in the full
registry: it asked which ticker the user meant (they'd said it) and claimed a
capability was missing (it was registered). Strong brains — claude-sdk,
Anthropic, real OpenAI — use everything. Local/compat endpoints get a curated
CORE set that still covers the daily conversation: portfolio, one symbol's
evidence, regime, exits, triage, sizing, price, brief, risk, journal.

Policy is settings-overridable (KUBERA_TOOL_PROFILE=auto|full|core) so the
owner can force either way without code changes. The curated set is guarded by
a test: every CORE name must exist in the registry, so a rename can't silently
shrink a small brain's capability.
"""

from settings import KuberaSettings

# The daily-conversation core: answer "how am I doing", "should I buy X",
# "how many shares", "what's my risk", "log this decision" — without the
# long tail (backtests, sweeps, attribution, correlation, macro, news…).
CORE_TOOLS = (
    "get_portfolio",
    "get_symbol_briefing",
    "get_latest",
    "get_regime",
    "get_exit_plan",
    "triage_position",
    "size_position",
    "get_brief",
    "get_risk_status",
    "record_decision",
    "get_ips",
)

SMALL_BRAIN_PROVIDERS = ("ollama", "local")   # explicit provider names, if ever added


def is_small_brain(settings: KuberaSettings) -> bool:
    """A brain is 'small' when it speaks the OpenAI wire format against a
    NON-OpenAI endpoint — i.e. a local runtime (Ollama, LM Studio, llama.cpp).
    claude-sdk / anthropic / real openai are all treated as strong."""
    provider = (settings.llm_provider or "").lower()
    if provider in SMALL_BRAIN_PROVIDERS:
        return True
    if provider == "openai":
        return "api.openai.com" not in (settings.openai_base_url or "")
    return False


def tool_names_for(settings: KuberaSettings, all_names: list[str]) -> list[str]:
    """Which registry tools this brain should be offered."""
    profile = (getattr(settings, "tool_profile", "auto") or "auto").lower()
    if profile == "full":
        return list(all_names)
    if profile == "core":
        return [n for n in all_names if n in CORE_TOOLS]
    if is_small_brain(settings):
        return [n for n in all_names if n in CORE_TOOLS]
    return list(all_names)


def filter_schemas(settings: KuberaSettings, schemas: list[dict]) -> list[dict]:
    allowed = set(tool_names_for(settings, [s["name"] for s in schemas]))
    return [s for s in schemas if s["name"] in allowed]
