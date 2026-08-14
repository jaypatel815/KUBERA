"""Nightly database backup (D018) — 10 lines of insurance for weeks of data.

Copies the SQLite database to backups/kubera-YYYYMMDD-HHMMSS.sqlite3 and prunes
old copies beyond --keep. Wire it to Windows Task Scheduler nightly:

    schtasks /Create /SC DAILY /ST 23:30 /TN "KUBERA backup" ^
        /TR "py C:\\Users\\jaybe\\Projects\\KUBERA\\scripts\\backup_db.py"

The backups/ folder is git-ignored — snapshots, signal logs, backtest ledger and
conversation history never belong in the repo.
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = REPO_ROOT / "kubera.sqlite3"
DEFAULT_DIR = REPO_ROOT / "backups"


def backup_database(
    db_path: Path, backup_dir: Path, keep: int, now: datetime | None = None
) -> tuple[Path, list[Path]]:
    """Copy db_path into backup_dir with a timestamped name; prune to `keep` newest.
    Returns (new_backup_path, pruned_paths). Raises FileNotFoundError if no DB."""
    if keep < 1:
        raise ValueError(f"keep must be >= 1, got {keep}")
    if not db_path.exists():
        raise FileNotFoundError(
            f"database not found at {db_path} — run the migrations/sync first"
        )
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    dest = backup_dir / f"{db_path.stem}-{stamp}{db_path.suffix}"
    shutil.copy2(db_path, dest)

    backups = sorted(backup_dir.glob(f"{db_path.stem}-*{db_path.suffix}"))
    pruned = backups[:-keep] if len(backups) > keep else []
    for old in pruned:
        old.unlink()
    return dest, pruned


def main() -> int:
    ap = argparse.ArgumentParser(description="Back up the KUBERA SQLite database.")
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--dir", type=Path, default=DEFAULT_DIR)
    ap.add_argument("--keep", type=int, default=14, help="backups to retain (default 14)")
    args = ap.parse_args()
    try:
        dest, pruned = backup_database(args.db, args.dir, args.keep)
    except (FileNotFoundError, ValueError) as e:
        print(f"BACKUP FAILED: {e}", file=sys.stderr)
        return 1
    print(f"backed up -> {dest}")
    if pruned:
        print(f"pruned {len(pruned)} old backup(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
