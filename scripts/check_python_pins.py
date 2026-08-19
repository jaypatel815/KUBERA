"""I032 — the declaration-parity check that would have kept CI green.

The uv-scaffold cleanup (a65c360) deleted `.python-version` believing it was
scaffold; it was the D025 SINGLE SOURCE OF TRUTH that CI's setup-python reads
(`python-version-file`), so CI failed at setup on every push after. Nothing
local noticed: the gate never checked that the declarations agree AND exist.

This check does, and verify.py runs it: `.python-version` must exist and
match pyrefly.toml's `python-version`. Exit 1 with a named fix otherwise.
(The file allows no comments — pyenv/setup-python parse it raw — so THIS
script is where its purpose is documented: it is not uv scaffold.)
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    pv = ROOT / ".python-version"
    if not pv.exists():
        print("PYTHON PIN MISSING: .python-version was deleted — CI's "
              "setup-python reads it (python-version-file) and fails without "
              "it (I032). Restore it with the version pyrefly.toml declares.")
        return 1
    version = pv.read_text(encoding="utf-8").strip()
    toml = (ROOT / "pyrefly.toml").read_text(encoding="utf-8")
    m = re.search(r'python-version\s*=\s*"([^"]+)"', toml)
    if not m:
        print("pyrefly.toml has no python-version — cannot check parity")
        return 1
    if m.group(1) != version:
        print(f"PYTHON PIN MISMATCH: .python-version says {version!r} but "
              f"pyrefly.toml says {m.group(1)!r} — D025 requires one truth; "
              "fix whichever is wrong.")
        return 1
    print(f"python pins agree: {version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
