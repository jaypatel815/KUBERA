"""I038 — the ambient-environment leak, pinned by name.

The owner's shell exported settings vars; `KuberaSettings(_env_file=None)`
read them (OS env outranks a disabled dotenv) and four missing-config tests
failed with DID NOT RAISE — on his machine only. The conftest fixture now
strips every settings-mapped var before tests run. These tests turn that
silent premise into named assertions: the NEXT leak fails HERE, with an
explanation, instead of as scattered DID-NOT-RAISEs on one machine."""

import os

from conftest import settings_env_names

from settings import KuberaSettings

# llm_claude_sdk.py re-injects the oauth token from SETTINGS into the
# process env at call time (os.environ.setdefault) — that is production
# behavior a chat test legitimately exercises, not an ambient leak. It is
# the ONLY settings var allowed to reappear mid-run.
_REEXPORTED_BY_PRODUCTION_CODE = {"CLAUDE_CODE_OAUTH_TOKEN"}


def test_empty_settings_are_actually_empty():
    # the premise ~29 call sites rely on: _env_file=None means NOTHING
    # configured — regardless of what the launching shell exported
    s = KuberaSettings(_env_file=None)
    leaked = {
        "EDGAR_CONTACT": s.edgar_contact,
        "FINNHUB_API_KEY": s.finnhub_api_key,
        "FMP_API_KEY": s.fmp_api_key,
        "SCHWAB_APP_KEY": s.schwab_app_key,
        "ALPACA_API_KEY_ID": s.alpaca_api_key_id,
        "ANTHROPIC_API_KEY": s.anthropic_api_key,
    }
    dirty = sorted(k for k, v in leaked.items() if v is not None)
    assert not dirty, (
        f"ambient environment leaked into empty test settings: {dirty} — "
        "the conftest fixture (_ambient_settings_env_stripped) should have "
        "removed these before any test ran (I038)")


def test_no_settings_env_var_survives_in_the_process():
    # two-sided: not just "settings look empty" but "the vars are GONE" —
    # covers every field and alias spelling, derived from the model, so a
    # field added next month is covered without editing this test
    survivors = sorted(n for n in settings_env_names()
                       if n in os.environ
                       and n not in _REEXPORTED_BY_PRODUCTION_CODE)
    assert survivors == [], (
        f"settings env vars present during tests: {survivors} — either the "
        "I038 fixture broke or something re-exported them mid-run (if a new "
        "production setdefault is legitimate, allowlist it HERE with the "
        "reason, like CLAUDE_CODE_OAUTH_TOKEN)")


def test_derivation_knows_both_alpaca_spellings():
    # the derivation must include alias spellings, not just field names —
    # the owner's .env uses ALPACA_API_KEY (the alias), and an alias the
    # fixture misses is exactly how this bug would come back
    names = settings_env_names()
    for required in ("ALPACA_API_KEY", "ALPACA_API_KEY_ID",
                     "EDGAR_CONTACT", "FINNHUB_API_KEY", "FMP_API_KEY",
                     "SCHWAB_APP_KEY", "LLM_PROVIDER",
                     "KUBERA_LLM_PROVIDER"):
        assert required in names, f"fixture derivation misses {required}"
