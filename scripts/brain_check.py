"""Which brain is KUBERA actually using? (I014 correction)

Owner's .env said claude-sdk, yet an error labeled "openai" appeared. That is
possible because these are three DIFFERENT questions, and this script answers
all three so nobody ever argues from inference again:

1. What does repo .env SAY?           -> intent
2. What would a NEW server use?       -> resolution (real env vars BEAT .env —
                                         pydantic-settings precedence)
3. What is the RUNNING server using?  -> only /health knows; a server keeps the
                                         provider it started with until restarted

Usage:  python scripts/brain_check.py
Never prints secret values — presence and length only (I003 discipline).
"""

import os
import sys
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from settings import KuberaSettings, env_file_llm_provider  # noqa: E402

ENV_VARS = ("KUBERA_LLM_PROVIDER", "LLM_PROVIDER")  # checked in alias order
DEFAULT_URL = "http://127.0.0.1:8000"


def main() -> int:
    print("KUBERA brain check")
    print("=" * 50)

    # 1. intent: repo .env
    intended = env_file_llm_provider(REPO_ROOT / ".env")
    print(f"1. .env says:            LLM_PROVIDER={intended or '(not set)'}")

    # 2. resolution: what a NEW process would use (env vars win over .env)
    overrides = [(v, os.environ[v]) for v in ENV_VARS if v in os.environ]
    for name, value in overrides:
        print(f"   !! OS environment has {name}={value} — this BEATS .env")
    resolved = KuberaSettings().llm_provider
    print(f"2. a NEW server would use: {resolved}")
    if intended and resolved != intended:
        print(f"   >> MISMATCH: .env says {intended!r} but resolution gives "
              f"{resolved!r} — an OS env var is overriding. Fix (PowerShell):")
        print("      Remove-Item Env:LLM_PROVIDER  # this shell")
        print("      [Environment]::SetEnvironmentVariable('LLM_PROVIDER', "
              "$null, 'User')  # permanently")

    # tokens present? (presence + length only, never values)
    for key in ("CLAUDE_CODE_OAUTH_TOKEN", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        s = KuberaSettings()
        attr = getattr(s, key.lower(), None)
        val = attr.get_secret_value() if hasattr(attr, "get_secret_value") else attr
        print(f"   {key}: {'set (' + str(len(val)) + ' chars)' if val else 'NOT set'}")

    # 3. the RUNNING server (the only answer that explains a live transcript)
    try:
        r = httpx.get(f"{DEFAULT_URL}/health", timeout=3.0)
        live = r.json().get("llm_provider", "(health endpoint predates I011)")
        print(f"3. RUNNING server uses:  {live}")
        if intended and live != intended:
            print("   >> The live server is NOT on your .env setting — it kept "
                  "the provider it started with, or its environment overrides. "
                  "Restart it from a clean shell and re-run this check.")
    except httpx.HTTPError:
        print(f"3. RUNNING server:       not reachable at {DEFAULT_URL} "
              "(start it, then re-run to see the live provider)")

    print("=" * 50)
    print("Rule of thumb: transcripts are explained by #3, never by #1.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
