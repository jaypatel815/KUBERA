"""Make /backend importable without an install step, so any agent can run
tests cold — and strip ambient settings env vars so tests mean what they say.

I038: on the owner's machine (2026-08-21), EDGAR_CONTACT / FINNHUB_API_KEY /
FMP_API_KEY / SCHWAB_* were exported in the shell itself. pydantic-settings
reads real OS environment variables at HIGHER priority than any dotenv file,
so `KuberaSettings(_env_file=None)` — the standard "empty settings" test
premise, used at ~29 call sites — silently picked the values up and four
missing-config tests failed with DID NOT RAISE, while CI and the review
sandbox (clean shells) stayed green. Same class as I036/I037: a truth that
depends on which machine is asking.

The fixture below deletes every env var KuberaSettings can read (derived
from the model itself, so NEW fields are covered automatically) before any
test runs. This is safe for live-keyed tests: those construct KuberaSettings
with the default `_env_file`, which reads the .env FILE directly — the file
does not care what the process environment held. The claude-sdk provider
re-injects its token from settings at call time (llm_claude_sdk.py), so no
consumer needs the ambient copy either.
"""

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest  # noqa: E402


def settings_env_names() -> set[str]:
    """Every OS env var name KuberaSettings can read: each field's UPPER
    name plus all of its declared alias spellings."""
    from pydantic import AliasChoices

    from settings import KuberaSettings

    names: set[str] = set()
    for field_name, field in KuberaSettings.model_fields.items():
        names.add(field_name.upper())
        alias = field.validation_alias
        if isinstance(alias, AliasChoices):
            names.update(str(c) for c in alias.choices)
        elif isinstance(alias, str):
            names.add(alias)
    return names


@pytest.fixture(autouse=True, scope="session")
def _ambient_settings_env_stripped():
    """I038 defense: the process environment is not part of any test's
    premise. Runs once, before the first test."""
    removed = sorted(n for n in settings_env_names() if n in os.environ)
    for name in removed:
        del os.environ[name]
    yield removed
