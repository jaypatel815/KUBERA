"""Parallel-work safety check (D023) — run it before you edit a shared file.

Two agents in ONE working directory never produce a git merge conflict: same
branch, sequential commits, nothing to merge. The real hazard is the SILENT
LOST UPDATE — agent A reads TASKS.md, agent B saves a change, A writes back
from its stale copy, and B's lines are gone with no warning at all.

This script surfaces what a human (or an agent) can't see by looking at a file:
  1. who has claimed what, from TASKS.md
  2. which shared hot-spot files are currently dirty (someone is mid-edit)
  3. whether recent commits DELETED lines from the memory files — the
     signature of a clobber
  4. whether alembic has more than one head

Usage:
    python scripts/parallel_check.py            # before you start editing
    python scripts/parallel_check.py --since 5  # scan more commits

Exit 0 = clear, 1 = something needs a human's eyes.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# Files every ticket tends to touch — the ones "just don't edit the same file"
# cannot protect, because both agents MUST write them.
HOT_FILES = [
    "project-memory/TASKS.md",
    "project-memory/PROGRESS.md",
    "project-memory/DECISIONS.md",
    "project-memory/ISSUES.md",
    "README.md",
    "AGENTS.md",
    "backend/tests/test_tools.py",
    "backend/tests/test_chat.py",
    "backend/tests/test_claude_sdk.py",
    "apps/web/orb.html",
]
APPEND_ONLY = {  # deletions here are almost always a clobber, not an edit
    "project-memory/PROGRESS.md",
    "project-memory/DECISIONS.md",
}


def git(*args: str) -> str:
    # T113: explicit utf-8 — Windows text=True defaults to cp1252, which
    # mangles or crashes on the em-dashes/middle-dots all over the memory
    # files this script exists to read. errors="replace" so a stray byte
    # degrades one character, never the whole safety check.
    return subprocess.run(["git", "-C", str(REPO), *args],
                          capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout.strip()


def parse_claims(tasks_text: str) -> list[str]:
    """`In progress — T072 — Claude` style lines, whatever the dash."""
    out = []
    for line in tasks_text.splitlines():
        s = line.strip().lstrip("-*[ ]x").strip()
        if re.match(r"(?i)^in progress\b", s) and not re.match(
                r"(?i)^in progress\s*$", s):
            out.append(s)
    return out


def deleted_lines(diff: str) -> int:
    """Count real deletions in a unified diff (ignore the ---/+++ headers)."""
    return sum(1 for ln in diff.splitlines()
               if ln.startswith("-") and not ln.startswith("---"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--since", type=int, default=3,
                    help="how many recent commits to scan for clobbers")
    args = ap.parse_args()

    problems: list[str] = []
    notes: list[str] = []

    print("KUBERA parallel-work check")
    print("=" * 58)

    # 1. who claimed what
    tasks = (REPO / "project-memory" / "TASKS.md")
    claims = parse_claims(tasks.read_text(encoding="utf-8")) if tasks.exists() else []
    if claims:
        print("Active claims in TASKS.md:")
        for c in claims:
            print(f"  · {c}")
        if len(claims) > 1:
            notes.append("more than one agent is mid-ticket — check their files "
                         "differ from yours before editing")
    else:
        print("Active claims: none recorded")

    # 2. dirty hot files = someone is editing RIGHT NOW
    dirty = git("status", "--porcelain")
    dirty_paths = {ln[3:].strip() for ln in dirty.splitlines() if ln.strip()}
    hot_dirty = sorted(p for p in dirty_paths if p in HOT_FILES)
    print()
    if hot_dirty:
        print("Shared files with UNCOMMITTED changes (another agent may be "
              "mid-edit — re-read immediately before you write):")
        for p in hot_dirty:
            print(f"  ! {p}")
        problems.append(f"{len(hot_dirty)} shared file(s) dirty — re-read before writing")
    else:
        print("Shared files: all clean")

    # 3. clobber signature — deletions in append-only memory files
    print()
    log = git("log", f"-{args.since}", "--format=%H|%an|%s")
    clobbers = []
    for line in log.splitlines():
        if not line:
            continue
        sha, author, subject = line.split("|", 2)
        for path in APPEND_ONLY:
            d = git("show", "--format=", "--unified=0", sha, "--", path)
            n = deleted_lines(d)
            if n > 2:  # a couple of lines can be a legitimate edit; a block isn't
                clobbers.append(f"{sha[:8]} ({author}) removed {n} lines from "
                                f"{path} — '{subject[:44]}'")
    if clobbers:
        print("Possible CLOBBERS in append-only memory files:")
        for c in clobbers:
            print(f"  ! {c}")
        print("  Recover with: git show <sha>^:<path> > /tmp/before.md, then "
              "re-add the missing block.")
        problems.append(f"{len(clobbers)} possible clobber(s) in memory files")
    else:
        print(f"No clobber signature in the last {args.since} commits")

    # 4. one alembic head, or migrations have branched
    print()
    heads = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", "heads"],
        capture_output=True, text=True, cwd=str(REPO / "backend"),
        encoding="utf-8", errors="replace",  # T113: same Windows cp1252 guard
    ).stdout.strip()
    head_lines = [h for h in heads.splitlines() if h.strip()]
    if len(head_lines) > 1:
        print("ALEMBIC HAS MULTIPLE HEADS — concurrent migrations branched:")
        for h in head_lines:
            print(f"  ! {h}")
        problems.append("alembic has >1 head; rebase the newer migration")
    elif head_lines:
        print(f"Alembic: single head ({head_lines[0].split()[0]})")
    else:
        print("Alembic: could not read heads (env not installed here?)")

    print("=" * 58)
    for n in notes:
        print(f"note: {n}")
    if problems:
        for p in problems:
            print(f"ATTENTION: {p}", file=sys.stderr)
        return 1
    print("Clear to edit. Still: re-read a shared file immediately before "
          "writing it, and stage by path.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
