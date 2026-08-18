"""T112 — enforce the memory bounds that existed on paper since day one (D031).

PROGRESS.md's own header has always said: "When this file exceeds ~150 lines,
move old entries to /project-memory/archive/." When this script was written,
the file stood at 2,654 lines and the archive directory did not exist — a rule
without a mechanism does not happen (the same lesson as D028's limit note, and
hermes-agent's bounded-memory design reviewed in
docs/research/hermes-agent-review-2026-08-17.md).

    python scripts/archive_memory.py            # archive old PROGRESS entries
    python scripts/archive_memory.py --check    # budgets only (verify.py runs this)
    python scripts/archive_memory.py --keep 12  # override how many entries stay

Rules (D031):
- MOVE, NEVER DELETE: archived entries go to project-memory/archive/
  PROGRESS-archive-<UTC-date>.md verbatim, newest-first, with a provenance
  header. git history is the snapshot; the move is an ordinary reviewable
  commit.
- Only CLOSED history is curated: the newest --keep entries (default 12) stay
  in PROGRESS.md untouched; the file's header block stays.
- The check is the mechanism: --check WARNS at soft budgets and FAILS at hard
  budgets, so overflow forces deliberate archiving instead of silent growth —
  hermes's error-forces-consolidation semantics, adapted.
- TASKS/ISSUES/DECISIONS get budgets (warn-only for now): their entries need
  judgment to compact, so the check nags and a human-or-agent session curates
  deliberately. PROGRESS is mechanical: entries are dated and append-only.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEMORY = ROOT / "project-memory"
ARCHIVE = MEMORY / "archive"

# (file, soft warn lines, hard fail lines, auto-archivable)
BUDGETS = [
    ("PROGRESS.md", 700, 1000, True),
    ("TASKS.md", 900, 1400, False),
    ("ISSUES.md", 700, 1100, False),
    ("DECISIONS.md", 900, 1400, False),
]

_ENTRY = re.compile(r"^## \d{4}-\d{2}-\d{2}", re.MULTILINE)


def split_progress(text: str) -> tuple[str, list[str]]:
    """(header-block, [entry blocks newest-first]) — entries start '## YYYY-MM-DD'."""
    starts = [m.start() for m in _ENTRY.finditer(text)]
    if not starts:
        return text, []
    header = text[: starts[0]]
    entries = [text[s:e] for s, e in zip(starts, starts[1:] + [len(text)])]
    return header, entries


def check() -> int:
    """Budget check for the verify gate: 0 ok, 1 warn, 2 fail."""
    worst = 0
    for name, soft, hard, auto in BUDGETS:
        n = len((MEMORY / name).read_text(encoding="utf-8").splitlines())
        if n > hard:
            print(f"MEMORY BUDGET FAIL: {name} is {n} lines (hard cap {hard}). "
                  + ("Run: python scripts/archive_memory.py" if auto else
                     "Curate it deliberately this session — move closed entries "
                     "to project-memory/archive/ (move, never delete)."))
            worst = max(worst, 2)
        elif n > soft:
            print(f"memory budget warning: {name} at {n} lines (soft {soft}, "
                  f"hard {hard})" + (" — archive_memory.py trims it" if auto else ""))
            worst = max(worst, 1)
    if worst == 0:
        print("memory budgets: all within bounds")
    return worst


def archive_progress(keep: int) -> int:
    path = MEMORY / "PROGRESS.md"
    text = path.read_text(encoding="utf-8")
    header, entries = split_progress(text)
    if len(entries) <= keep:
        print(f"PROGRESS.md has {len(entries)} entries (keep={keep}) — nothing to archive")
        return 0

    stay, move = entries[:keep], entries[keep:]
    ARCHIVE.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).date().isoformat()
    out = ARCHIVE / f"PROGRESS-archive-{stamp}.md"
    # Never overwrite an existing archive file silently.
    i = 2
    while out.exists():
        out = ARCHIVE / f"PROGRESS-archive-{stamp}-{i}.md"
        i += 1

    out.write_text(
        f"# PROGRESS archive — moved {stamp} by scripts/archive_memory.py (T112/D031)\n"
        f"# {len(move)} entries, verbatim, newest-first. MOVED, never deleted;\n"
        f"# the removal commit in PROGRESS.md is the other half of this diff.\n\n"
        + "".join(move),
        encoding="utf-8",
    )
    path.write_text(header + "".join(stay), encoding="utf-8")
    out_label = out.relative_to(ROOT) if out.is_relative_to(ROOT) else out
    print(f"archived {len(move)} PROGRESS entries -> {out_label}")
    print(f"PROGRESS.md now {len(path.read_text(encoding='utf-8').splitlines())} lines "
          f"({keep} newest entries kept)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Curate project memory (T112, D031).")
    ap.add_argument("--check", action="store_true", help="budgets only (verify gate)")
    ap.add_argument("--keep", type=int, default=12,
                    help="newest PROGRESS entries to keep in place")
    args = ap.parse_args()
    if args.check:
        return 2 if check() == 2 else 0   # warnings don't fail the gate; hard caps do
    if args.keep < 5:
        print("refusing --keep < 5: the resume protocol needs recent context")
        return 2
    return archive_progress(args.keep)


if __name__ == "__main__":
    sys.exit(main())
