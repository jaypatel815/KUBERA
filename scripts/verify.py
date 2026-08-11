"""The single verification gate. Green here = allowed to end a session (AGENTS.md).

Usage (any OS):  python scripts/verify.py
CI runs exactly this same script.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STEPS = [
    ("lint (ruff)", [sys.executable, "-m", "ruff", "check", "backend", "scripts"]),
    ("tests (pytest)", [sys.executable, "-m", "pytest", "backend/tests", "-q"]),
]


def main() -> int:
    failed = []
    for name, cmd in STEPS:
        print(f"\n=== {name} ===")
        if subprocess.run(cmd, cwd=ROOT).returncode != 0:
            failed.append(name)
    print("\nVERIFY:", "PASS — safe to commit" if not failed else f"FAIL — {', '.join(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
