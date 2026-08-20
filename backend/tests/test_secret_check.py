"""T130 — the secrets checker: every detector proven able to FIRE on planted
fixtures (a checker that can't find anything is indistinguishable from a
clean repo, D027 #3), then the REAL repo pinned clean — so any future commit
that trips it turns the suite red.

First live run already earned its keep: it found three credential fields
(anthropic/openai/claude_code_oauth_token) absent from .env.example — the
exact T114/FMP_API_KEY class of bug, mechanized.
"""

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "secret_check.py"

spec = importlib.util.spec_from_file_location("secret_check_t130", SCRIPT)
assert spec is not None and spec.loader is not None
sc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sc)


# --- detectors fire on planted fixtures -------------------------------------

def test_scan_finds_each_pattern_class():
    planted = "\n".join([
        "aws = 'AKIA" + "ABCDEFGHIJKLMNOP'",
        "gh = 'ghp_" + "a" * 36 + "'",
        "-----BEGIN RSA PRIVATE KEY-----",
        'api_key = "' + "f0e1d2c3b4a5968778695a4b3c2d1e0f" + '"',
    ])
    findings = sc.scan_content("planted.py", planted)
    names = " ".join(findings)
    # the AKIA plant legitimately trips TWO detectors (aws + alpaca-shaped);
    # over-detection on a real key is a feature, so assert names, not counts
    assert len(findings) >= 4
    assert "aws-access-key" in names and "github-token" in names
    assert "private-key-pem" in names and "credential-assignment" in names
    # file:line present, VALUE never echoed
    assert "planted.py:1" in names
    assert "AKIA" not in " ".join(f.split(":")[2] for f in findings)


def test_scan_skips_placeholders():
    text = 'FMP_API_KEY = "your-key-goes-here-really"\napi_key = "<paste-your-key-here>"'
    assert sc.scan_content(".env.example", text) == []


def test_example_vars_reads_plain_and_commented_convention():
    text = ("# prose line about keys\n"
            "FRED_API_KEY=\n"
            "# OPENAI_API_KEY=\n"
            "#   ALPACA_PAPER=true\n"
            "not_a_var line\n")
    assert sc.example_vars(text) == {"FRED_API_KEY", "OPENAI_API_KEY",
                                     "ALPACA_PAPER"}


# --- parity + floor ---------------------------------------------------------

def _spec(name, envs, secret):
    return (name, envs, secret)


def test_parity_flags_dead_documentation_and_missing_credentials():
    specs = [_spec("fmp_api_key", ["FMP_API_KEY"], True),
             _spec("alpaca_paper", ["ALPACA_PAPER"], False)]
    findings = sc.check_parity(specs, {"ALPACA_PAPER", "GHOST_VAR"})
    text = " ".join(findings)
    assert "GHOST_VAR" in text and "never reads it" in text
    assert "fmp_api_key" in text and "not documented" in text


def test_parity_accepts_documentation_via_alias():
    specs = [_spec("alpaca_api_secret_key",
                   ["ALPACA_API_SECRET_KEY", "ALPACA_SECRET_KEY"], True)]
    assert sc.check_parity(specs, {"ALPACA_SECRET_KEY"}) == []


def test_secretstr_floor_scope():
    specs = [
        _spec("schwab_refresh_token", ["X1"], False),   # MUST be SecretStr
        _spec("fred_api_key", ["X2"], True),            # is — fine
        _spec("schwab_token_url", ["X3"], False),       # URL, not a secret
        _spec("alpaca_api_key_id", ["X4"], False),      # identifier by design
    ]
    findings = sc.check_secretstr_floor(specs)
    assert len(findings) == 1 and "schwab_refresh_token" in findings[0]


# --- the real repo, pinned clean --------------------------------------------

def test_the_actual_repo_is_clean():
    """The whole checker against the WHOLE repo, inside the suite: a future
    commit that plants a key-shaped string, documents a ghost var, or adds
    an undocumented credential turns the test suite red."""
    assert sc.main([]) == 0
