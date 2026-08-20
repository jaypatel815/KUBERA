"""T124 — the restore drill, drilled: fixture SQLite files prove every verdict
path (PASS / FAIL / WARN) and the pure comparison logic.

Loaded importlib-by-path per the T113/T106 precedent — no sys.path mutation.
All databases live in tmp_path; the real repo DB and backups are never touched.
"""

import importlib.util
import sqlite3
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "restore_check.py"

spec = importlib.util.spec_from_file_location("restore_check_t124", SCRIPT)
assert spec is not None and spec.loader is not None
rc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rc)


def _make_db(path: Path, tables: dict[str, int]) -> None:
    """A real sqlite file with `tables` = {name: row count}."""
    con = sqlite3.connect(path)
    try:
        for name, rows in tables.items():
            con.execute(f'CREATE TABLE "{name}" (id INTEGER PRIMARY KEY, v TEXT)')
            con.executemany(
                f'INSERT INTO "{name}" (v) VALUES (?)', [("x",)] * rows
            )
        con.commit()
    finally:
        con.close()


def _setup(tmp_path, live_tables, backup_tables, stamp="20260820-120000"):
    """Live DB + one backup under the real naming convention. Either side can
    be None to leave that file absent."""
    live = tmp_path / "kubera.sqlite3"
    bdir = tmp_path / "backups"
    bdir.mkdir()
    if live_tables is not None:
        _make_db(live, live_tables)
    if backup_tables is not None:
        _make_db(bdir / f"kubera-{stamp}.sqlite3", backup_tables)
    return live, bdir


def test_identical_backup_passes(tmp_path, capsys):
    tables = {"positions": 3, "journal": 7, "alembic_version": 1}
    live, bdir = _setup(tmp_path, tables, tables)
    code = rc.main(["--db", str(live), "--backups", str(bdir)])
    out = capsys.readouterr().out
    assert code == 0 and "RESTORE: PASS" in out
    assert "integrity     : ok" in out


def test_lagging_counts_still_pass(tmp_path, capsys):
    # a snapshot is ALLOWED to be behind — that is what a snapshot is
    live, bdir = _setup(tmp_path, {"journal": 10}, {"journal": 6})
    code = rc.main(["--db", str(live), "--backups", str(bdir)])
    out = capsys.readouterr().out
    assert code == 0 and "lags live" in out


def test_schema_drift_warns(tmp_path, capsys):
    # live gained a table since the backup: restoring would serve old schema
    live, bdir = _setup(
        tmp_path, {"journal": 5, "new_after_migration": 0}, {"journal": 5}
    )
    code = rc.main(["--db", str(live), "--backups", str(bdir)])
    out = capsys.readouterr().out
    assert code == 2 and "DRIFT" in out and "alembic upgrade head" in out


def test_corrupt_backup_fails(tmp_path, capsys):
    live, bdir = _setup(tmp_path, {"journal": 2}, None)
    (bdir / "kubera-20260820-120000.sqlite3").write_bytes(b"not a database at all")
    code = rc.main(["--db", str(live), "--backups", str(bdir)])
    out = capsys.readouterr().out
    assert code == 1 and "RESTORE: FAIL" in out


def test_no_backups_is_a_named_refusal(tmp_path, capsys):
    live, bdir = _setup(tmp_path, {"journal": 2}, None)
    code = rc.main(["--db", str(live), "--backups", str(bdir)])
    out = capsys.readouterr().out
    assert code == 1 and "no backups matching" in out and "backup_db.py" in out


def test_missing_live_db_warns_not_fails(tmp_path, capsys):
    # backup is sound; there is just nothing to compare — a fresh machine
    live, bdir = _setup(tmp_path, None, {"journal": 4})
    code = rc.main(["--db", str(live), "--backups", str(bdir)])
    out = capsys.readouterr().out
    assert code == 2 and "no live" in out


def test_newest_backup_is_by_timestamp_name(tmp_path):
    live, bdir = _setup(tmp_path, None, {"journal": 1}, stamp="20260819-233000")
    _make_db(bdir / "kubera-20260820-233000.sqlite3", {"journal": 2})
    _make_db(bdir / "other-20260821-000000.sqlite3", {"journal": 9})  # wrong stem
    picked = rc.newest_backup(bdir, live)
    assert picked is not None and picked.name == "kubera-20260820-233000.sqlite3"


def test_compare_counts_is_pure_and_directional():
    lines, drift = rc.compare_counts({"a": 1}, {"a": 1, "b": 2})
    assert drift is True and any("MISSING" in ln and "b" in ln for ln in lines)
    # table dropped from live is noted but NOT drift — restoring loses nothing
    lines, drift = rc.compare_counts({"a": 1, "old": 3}, {"a": 1})
    assert drift is False and any("dropped since backup" in ln for ln in lines)
