"""T124 — backup RESTORE drill: a backup nobody has restored is a hope.

backup_db.py (D018) has copied kubera.sqlite3 nightly for weeks, and nothing
has ever proven those copies restore. This script is the other half of the
insurance: take the NEWEST backups/kubera-*.sqlite3, copy it to a scratch
directory exactly as a real restore would, then interrogate the copy —
PRAGMA integrity_check must say "ok", and every table the LIVE database has
must exist in the backup (a missing table means the backup predates a
migration: it would restore yesterday's schema under today's code).

Row counts are printed per table but only INFORM — a backup is a snapshot,
so lagging counts are expected, not an error. Schedulable exit codes:

    0  PASS — the newest backup restores and matches the live schema
    1  FAIL — no backup, unreadable file, or integrity_check != ok
    2  WARN — restores, but schema drift vs live (or no live DB to compare)

Wire it to Task Scheduler right after the nightly backup:

    schtasks /Create /SC DAILY /ST 23:45 /TN "KUBERA restore check" ^
        /TR "py C:\\Users\\jaybe\\Projects\\KUBERA\\scripts\\restore_check.py"

Everything here opens databases READ-ONLY (mode=ro URI) and writes only to a
temp directory that is deleted on exit — the drill can never hurt the data
it exists to protect.
"""

import argparse
import shutil
import sqlite3
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = REPO_ROOT / "kubera.sqlite3"
DEFAULT_DIR = REPO_ROOT / "backups"

PASS, FAIL, WARN = 0, 1, 2


def newest_backup(backup_dir: Path, db_path: Path) -> Path | None:
    """Newest backup by name — timestamps are fixed-width (YYYYMMDD-HHMMSS),
    so lexicographic order IS chronological order (same assumption
    backup_db.py's prune relies on). None if there are no backups."""
    if not backup_dir.is_dir():
        return None
    backups = sorted(backup_dir.glob(f"{db_path.stem}-*{db_path.suffix}"))
    return backups[-1] if backups else None


def _connect_ro(db: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)


def integrity_check(db: Path) -> tuple[bool, str]:
    """PRAGMA integrity_check on a read-only connection.
    Returns (ok, detail) — detail carries sqlite's own words on failure."""
    try:
        con = _connect_ro(db)
        try:
            rows = con.execute("PRAGMA integrity_check").fetchall()
        finally:
            con.close()
    except sqlite3.Error as e:
        return False, f"not a readable sqlite database: {e}"
    msgs = [str(r[0]) for r in rows]
    return msgs == ["ok"], "; ".join(msgs)


def table_counts(db: Path) -> dict[str, int]:
    """{table: row count} for user tables, read-only. sqlite_* internals and
    alembic bookkeeping stay in — alembic_version is exactly the table whose
    presence proves which migration the backup was taken under."""
    con = _connect_ro(db)
    try:
        names = [
            str(r[0])
            for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        return {
            n: int(con.execute(f'SELECT COUNT(*) FROM "{n}"').fetchone()[0])
            for n in names
        }
    finally:
        con.close()


def compare_counts(
    backup: dict[str, int], live: dict[str, int]
) -> tuple[list[str], bool]:
    """Per-table comparison lines + whether schema DRIFT exists (live tables
    absent from the backup). Lagging row counts are labeled, never fatal.
    Pure — unit-tested directly."""
    drift = False
    lines: list[str] = []
    for name in sorted(set(backup) | set(live)):
        b, li = backup.get(name), live.get(name)
        if li is None:
            lines.append(f"  {name:<28} backup={b:<8} live=MISSING (dropped since backup?)")
        elif b is None:
            drift = True
            lines.append(f"  {name:<28} backup=MISSING live={li} <- DRIFT: predates a migration")
        else:
            if b == li:
                note = ""
            elif b < li:
                note = " (lags live - expected for a snapshot)"
            else:
                note = " (ahead of live?)"
            lines.append(f"  {name:<28} backup={b:<8} live={li}{note}")
    return lines, drift


def run_drill(db_path: Path, backup_dir: Path) -> int:
    backup = newest_backup(backup_dir, db_path)
    if backup is None:
        print(
            f"RESTORE: FAIL — no backups matching {db_path.stem}-*{db_path.suffix} "
            f"in {backup_dir} (run scripts/backup_db.py first)"
        )
        return FAIL

    print(f"newest backup : {backup.name} ({backup.stat().st_size:,} bytes)")
    with tempfile.TemporaryDirectory(prefix="kubera_restore_") as tmp:
        restored = Path(tmp) / db_path.name
        shutil.copy2(backup, restored)  # the actual restore motion
        print(f"restored to   : scratch copy ({restored.stat().st_size:,} bytes)")

        ok, detail = integrity_check(restored)
        if not ok:
            print(f"RESTORE: FAIL — integrity_check on the copy: {detail}")
            return FAIL
        print("integrity     : ok")

        try:
            bcounts = table_counts(restored)
        except sqlite3.Error as e:
            print(f"RESTORE: FAIL — could not enumerate tables: {e}")
            return FAIL
        if not bcounts:
            print("RESTORE: FAIL — backup contains ZERO tables (an empty shell restores nothing)")
            return FAIL

        if not db_path.exists():
            print(f"tables        : {len(bcounts)} in backup")
            print(
                "RESTORE: WARN — backup is internally sound but there is no live "
                f"database at {db_path} to compare schemas against"
            )
            return WARN

        lcounts = table_counts(db_path)
        lines, drift = compare_counts(bcounts, lcounts)
        print(f"tables        : {len(bcounts)} in backup, {len(lcounts)} live")
        for line in lines:
            print(line)
        if drift:
            print(
                "RESTORE: WARN — schema drift: the backup predates a migration; "
                "a restore would need `alembic upgrade head` before serving"
            )
            return WARN

    print("RESTORE: PASS — the newest backup restores cleanly and matches the live schema")
    return PASS


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Prove the newest KUBERA backup actually restores."
    )
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--backups", type=Path, default=DEFAULT_DIR)
    args = ap.parse_args(argv)
    return run_drill(args.db, args.backups)


if __name__ == "__main__":
    raise SystemExit(main())
