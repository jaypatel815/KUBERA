"""Unit tests for scripts/archive_memory.py (T112 / D031)."""

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import archive_memory  # noqa: E402

SAMPLE_PROGRESS = """# PROGRESS

Newest entry on top.

## 2026-08-18 — Entry Three
Third entry details.

## 2026-08-17 — Entry Two
Second entry details.

## 2026-08-16 — Entry One
First entry details.
"""


def test_split_progress_splits_entries():
    header, entries = archive_memory.split_progress(SAMPLE_PROGRESS)
    assert "# PROGRESS" in header
    assert len(entries) == 3
    assert entries[0].startswith("## 2026-08-18 — Entry Three")
    assert entries[1].startswith("## 2026-08-17 — Entry Two")
    assert entries[2].startswith("## 2026-08-16 — Entry One")


def test_split_progress_no_entries():
    header, entries = archive_memory.split_progress("# Empty header only\n")
    assert header == "# Empty header only\n"
    assert entries == []


def test_archive_progress_moves_older_entries(tmp_path, monkeypatch):
    memory_dir = tmp_path / "project-memory"
    memory_dir.mkdir()
    progress_file = memory_dir / "PROGRESS.md"
    progress_file.write_text(SAMPLE_PROGRESS, encoding="utf-8")

    monkeypatch.setattr(archive_memory, "ROOT", tmp_path)
    monkeypatch.setattr(archive_memory, "MEMORY", memory_dir)
    monkeypatch.setattr(archive_memory, "ARCHIVE", memory_dir / "archive")

    # Keep 1 entry -> moves 2 entries
    res = archive_memory.archive_progress(keep=1)
    assert res == 0

    # Verify PROGRESS.md now only has header + Entry Three
    remaining = progress_file.read_text(encoding="utf-8")
    assert "Entry Three" in remaining
    assert "Entry Two" not in remaining
    assert "Entry One" not in remaining

    # Verify archive file created with Entry Two & One
    archive_dir = memory_dir / "archive"
    assert archive_dir.exists()
    archived_files = list(archive_dir.glob("PROGRESS-archive-*.md"))
    assert len(archived_files) == 1
    archive_content = archived_files[0].read_text(encoding="utf-8")
    assert "Entry Two" in archive_content
    assert "Entry One" in archive_content
    assert "MOVED, never deleted" in archive_content


def test_refuse_keep_less_than_five(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["archive_memory.py", "--keep", "3"])
    assert archive_memory.main() == 2
