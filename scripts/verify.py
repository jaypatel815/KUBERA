"""The single verification gate. Green here = allowed to end a session (AGENTS.md).

Usage (any OS):  python scripts/verify.py
CI runs exactly this same script.

WHY THE ENVIRONMENT BANNER EXISTS (I016, I018 — twice in one day):
A green suite means nothing until you know WHICH machine it ran on. Both bugs
that escaped this gate had the same shape — something present on the developer's
box and absent on a fresh checkout:

  I016  a test imported soundfile at module scope. Fine locally, aborted
        collection for the ENTIRE suite anywhere the optional voice deps were
        not installed.
  I018  a test overrode one of an endpoint's two dependencies. The other one
        needed Alpaca credentials, so it passed on any machine with a .env and
        returned 503 on CI. It sat red for ~80 tickets because nobody pushed.

So the gate now says out loud what it had available. When one agent reports PASS
and another reports FAIL, the banners make the difference visible immediately
instead of after an afternoon of bisecting.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STEPS = [
    ("lint (ruff)", [sys.executable, "-m", "ruff", "check", "backend", "scripts"]),
    ("tests (pytest)", [sys.executable, "-m", "pytest", "backend/tests", "-q"]),
    # T112/D031: memory files have budgets; overflow past the hard cap FAILS
    # the gate so a session must archive deliberately (move, never delete)
    # instead of letting the shared memory grow unreadable. PROGRESS.md hit
    # 2,654 lines against its own stated ~150 before this became mechanical.
    ("memory budgets", [sys.executable, "scripts/archive_memory.py", "--check"]),
    ("python pins (I032)", [sys.executable, "scripts/check_python_pins.py"]),
    # T125/I023: the type checker's zero is a GATE, not a habit — it has
    # caught four real bugs pre-commit; the wrapper parses the count so a
    # format drift fails loud instead of passing silent.
    ("types (pyrefly = exactly 0)", [sys.executable, "scripts/check_pyrefly.py"]),
]

# Things whose presence changes the result. Not a dependency list — a list of
# lies a green run can tell you.
OPTIONAL_MODULES = ("numpy", "soundfile", "kokoro_onnx", "edge_tts", "claude_agent_sdk")


def _environment_lines() -> list[str]:
    import platform

    lines = [
        f"python   {platform.python_version()} on {platform.system()}",
        f"root     {ROOT}",
    ]

    # A .env means the tests can reach real settings. CI has none, so anything
    # that quietly depends on one passes here and fails there.
    env_state = (
        "PRESENT — CI has none; a test needing it passes only here"
        if (ROOT / ".env").exists()
        else "absent (same as CI)"
    )
    lines.append(f".env     {env_state}")

    present = []
    for name in OPTIONAL_MODULES:
        try:
            __import__(name)
            present.append(name)
        except Exception:
            pass
    lines.append(f"optional {', '.join(present) if present else 'none installed (same as CI)'}")

    model_dir = ROOT / "models" / "kokoro"
    if model_dir.exists():
        lines.append("models   kokoro voice model PRESENT (absent in CI — gitignored)")

    return lines


def main() -> int:
    print("=== environment (read this before trusting a PASS) ===")
    for line in _environment_lines():
        print(f"  {line}")

    failed = []
    for name, cmd in STEPS:
        print(f"\n=== {name} ===")
        if subprocess.run(cmd, cwd=ROOT).returncode != 0:
            failed.append(name)

    print("\nVERIFY:", "PASS — safe to commit" if not failed else f"FAIL — {', '.join(failed)}")
    if not failed and (ROOT / ".env").exists():
        print(
            "  NOTE: this run had a .env. CI does not. If you touched an endpoint's\n"
            "  dependencies or added a test that hits one, confirm CI is green too."
        )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
