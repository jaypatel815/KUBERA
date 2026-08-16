"""Why isn't my .env being read? (companion to brain_check.py)

    python scripts/env_check.py
    python scripts/env_check.py SCHWAB       # only keys containing SCHWAB

Prints NAMES and VALUE LENGTHS. Never values — a diagnostic that leaks the thing
it is diagnosing is worse than no diagnostic (AGENTS.md).

It answers the four questions that account for nearly every "but it IS in my
.env" report, in the order they bite on Windows:

  1. WHICH FILE is being read? Settings uses an absolute path to the repo root,
     so a .env sitting next to your terminal's working directory is ignored.
  2. IS IT REALLY CALLED .env? Notepad's "Save As" adds .txt unless you quote the
     filename. `.env.txt` looks identical in Explorer with extensions hidden.
  3. DID AN EDITOR ADD A BOM or save as UTF-16? python-dotenv reads UTF-8; a
     UTF-16 file parses as garbage and a BOM corrupts the FIRST key name only,
     which is why the symptom is often "one variable is missing".
  4. IS THE KEY PRESENT BUT EMPTY, or shadowed by a real OS environment
     variable? OS variables WIN over .env (that was I015).
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from settings import KuberaSettings, get_settings  # noqa: E402


def _describe(value) -> str:
    if value is None:
        return "unset"
    text = value.get_secret_value() if hasattr(value, "get_secret_value") else str(value)
    return f"set, {len(text)} chars" if text else "SET BUT EMPTY"


def main() -> int:
    needle = (sys.argv[1] if len(sys.argv) > 1 else "").upper()
    env_path = Path(KuberaSettings.model_config.get("env_file", ROOT / ".env"))

    print("=== the file settings actually reads ===")
    print(f"  path    {env_path}")
    print(f"  exists  {env_path.exists()}")

    if not env_path.exists():
        print("\n  THAT IS THE PROBLEM. Look for a near-miss next to it:")
        for sibling in sorted(ROOT.glob(".env*")):
            print(f"    found: {sibling.name}")
        print("  Windows tip: Notepad saves '.env' as '.env.txt' unless you put the")
        print("  filename in double quotes in the Save As box.")
        return 2

    raw = env_path.read_bytes()
    print(f"  size    {len(raw)} bytes")
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        print("\n  UTF-16 BOM DETECTED — this file cannot be parsed as UTF-8.")
        print("  Re-save it as UTF-8: in Notepad, Save As -> Encoding: UTF-8.")
        return 2
    if raw.startswith(b"\xef\xbb\xbf"):
        print("  note: UTF-8 BOM present — harmless for every key EXCEPT the first line.")

    # What is literally in the file, by name only.
    print("\n=== keys present in the file (names and lengths only) ===")
    seen = {}
    for n, line in enumerate(raw.decode("utf-8", errors="replace").splitlines(), 1):
        stripped = line.strip().lstrip("﻿")
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, _, value = stripped.partition("=")
        name = name.strip()
        if needle and needle not in name.upper():
            continue
        seen[name] = value.strip()
        flag = ""
        if not value.strip():
            flag = "   <-- EMPTY"
        elif value.strip()[0] in "\"'" and value.strip()[-1] not in "\"'":
            flag = "   <-- UNBALANCED QUOTE"
        elif name != name.strip() or " " in name:
            flag = "   <-- SPACE IN THE NAME"
        print(f"  line {n:>3}  {name:<28} {len(value.strip()):>4} chars{flag}")
    if not seen:
        print("  (no matching keys found in the file — check spelling)")

    # What pydantic actually resolved, which is what the code sees.
    print("\n=== what settings resolved (this is what the code sees) ===")
    s = get_settings()
    fields = [f for f in type(s).model_fields if not needle or needle.lower() in f]
    for field in sorted(fields):
        print(f"  {field:<28} {_describe(getattr(s, field, None))}")

    # OS variables beat .env — the I015 trap.
    shadowed = [k for k in seen if os.environ.get(k) is not None]
    if shadowed:
        print("\n  WARNING — these are ALSO set as real OS environment variables,")
        print("  which OVERRIDE .env (I015). The file is not what you are running:")
        for k in shadowed:
            print(f"    {k}")

    print("\nIf a key shows in the file but 'unset' above, the usual causes are a")
    print("typo in the name, an OS variable shadowing it, or a stray quote earlier")
    print("in the file swallowing the following lines.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
