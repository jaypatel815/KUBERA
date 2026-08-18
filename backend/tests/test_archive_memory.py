"""T113 — pin scripts/archive_memory.py (T112/D031), the gate's memory mechanism.

Loaded importlib-by-path per the T106 precedent (test_install_mcp_config.py):
no sys.path mutation, nothing leaks into the rest of the suite. All paths are
monkeypatched onto tmp_path — these tests never touch the real project memory.
"""

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "archive_memory.py"

HEADER = (
    "# PROGRESS\n\n"
    "Newest entry on top. One dated entry per session.\n\n"
)


def _entry(day: int, body: str = "did a thing\n") -> str:
    return f"## 2026-08-{day:02d} — Agent — session\n{body}\n"


def _mod():
    spec = importlib.util.spec_from_file_location("archive_memory_t113", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def mem(tmp_path, monkeypatch):
    """Module wired to a scratch project-memory with 20 dated entries."""
    mod = _mod()
    memory = tmp_path / "project-memory"
    memory.mkdir()
    entries = [_entry(d) for d in range(20, 0, -1)]  # newest (day 20) first
    (memory / "PROGRESS.md").write_text(HEADER + "".join(entries), encoding="utf-8")
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    monkeypatch.setattr(mod, "MEMORY", memory)
    monkeypatch.setattr(mod, "ARCHIVE", memory / "archive")
    return mod, memory


def test_archive_preserves_header_and_keep_count(mem, capsys):
    """The two behaviours T112's reviewer flagged as worth pinning: the header
    block survives verbatim, and exactly `keep` newest entries stay in place —
    everything else lands in the archive file verbatim, newest-first."""
    mod, memory = mem
    assert mod.archive_progress(keep=12) == 0

    text = (memory / "PROGRESS.md").read_text(encoding="utf-8")
    assert text.startswith(HEADER)                      # header untouched
    assert text.count("## 2026-08-") == 12              # keep-count exact
    assert "## 2026-08-20" in text and "## 2026-08-09" in text
    assert "## 2026-08-08" not in text                  # 13th newest moved out

    archives = list((memory / "archive").glob("PROGRESS-archive-*.md"))
    assert len(archives) == 1
    archived = archives[0].read_text(encoding="utf-8")
    assert archived.count("## 2026-08-") == 8           # 20 - 12, nothing lost
    # Verbatim move, newest-first within the archive:
    assert archived.index("## 2026-08-08") < archived.index("## 2026-08-01")
    assert _entry(8) in archived
    # Provenance header names the mover and the rule:
    assert "archive_memory.py (T112/D031)" in archived.splitlines()[0]


def test_second_archive_same_day_never_overwrites(mem):
    """Two archives on one UTC date must produce TWO files — silent overwrite
    of moved history would be exactly the deletion D031 forbids."""
    mod, memory = mem
    assert mod.archive_progress(keep=12) == 0           # 8 entries -> file 1
    assert mod.archive_progress(keep=5) == 0            # 7 more    -> file 2
    archives = sorted((memory / "archive").glob("PROGRESS-archive-*.md"))
    assert len(archives) == 2
    # One base name, one "-2" suffix (don't assume sort order: "-" < ".").
    assert sum(1 for a in archives if a.stem.endswith("-2")) == 1
    total = sum(a.read_text(encoding="utf-8").count("## 2026-08-")
                for a in archives)
    kept = (memory / "PROGRESS.md").read_text(encoding="utf-8").count("## 2026-08-")
    assert total + kept == 20                           # move, never delete


def test_nothing_to_archive_is_a_clean_no_op(mem, capsys):
    mod, memory = mem
    before = (memory / "PROGRESS.md").read_text(encoding="utf-8")
    assert mod.archive_progress(keep=25) == 0
    assert (memory / "PROGRESS.md").read_text(encoding="utf-8") == before
    assert not (memory / "archive").exists()
    assert "nothing to archive" in capsys.readouterr().out


def test_check_levels_ok_warn_fail(tmp_path, monkeypatch, capsys):
    """--check is what verify.py runs: 0 within bounds, 1 past soft, 2 past
    hard. Only the hard cap may fail the gate (main maps 1 -> 0)."""
    mod = _mod()
    memory = tmp_path / "project-memory"
    memory.mkdir()
    monkeypatch.setattr(mod, "MEMORY", memory)

    def write_all(progress_lines: int):
        for name, _soft, _hard, _auto in mod.BUDGETS:
            n = progress_lines if name == "PROGRESS.md" else 10
            (memory / name).write_text("x\n" * n, encoding="utf-8")

    write_all(100)
    assert mod.check() == 0
    assert "within bounds" in capsys.readouterr().out

    write_all(701)                                      # soft 700
    assert mod.check() == 1
    assert "warning" in capsys.readouterr().out

    write_all(1001)                                     # hard 1000
    assert mod.check() == 2
    assert "FAIL" in capsys.readouterr().out


def test_split_progress_without_entries_is_all_header():
    mod = _mod()
    header, entries = mod.split_progress("# PROGRESS\n\njust prose, no dates\n")
    assert entries == []
    assert header.startswith("# PROGRESS")
