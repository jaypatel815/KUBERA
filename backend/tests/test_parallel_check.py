"""D023 parallel-check helpers — the pure parts, so the guard itself is trusted."""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "parallel_check", REPO / "scripts" / "parallel_check.py")
pc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pc)


# --- claim parsing ------------------------------------------------------------

def test_parses_claims_with_any_dash_and_bullet():
    text = """## In progress
- In progress — T072 — Claude
* In progress - T091b - Gemini
"""
    claims = pc.parse_claims(text)
    assert len(claims) == 2
    assert "T072" in claims[0] and "Claude" in claims[0]
    assert "T091b" in claims[1] and "Gemini" in claims[1]


def test_bare_in_progress_heading_is_not_a_claim():
    # the section header itself, and the "(none)" placeholder, must not count
    assert pc.parse_claims("## In progress\n(none)\n") == []
    assert pc.parse_claims("In progress\n") == []


def test_unrelated_lines_ignored():
    assert pc.parse_claims("- [x] T060 — done\nwork in progress somewhere\n") == []


# --- clobber detection --------------------------------------------------------

def test_deleted_lines_ignores_diff_headers():
    diff = """--- a/project-memory/PROGRESS.md
+++ b/project-memory/PROGRESS.md
@@ -1,4 +1,3 @@
-old line one
-old line two
+new line
 context
"""
    # the '---' header must NOT be counted as a deletion
    assert pc.deleted_lines(diff) == 2


def test_no_deletions_reads_zero():
    assert pc.deleted_lines("+++ b/x\n+added\n context\n") == 0


# --- the hot-file list is the point of the whole exercise ---------------------

def test_hot_files_cover_the_unavoidable_shared_ones():
    for must in ("project-memory/TASKS.md", "project-memory/PROGRESS.md",
                 "README.md", "apps/web/orb.html"):
        assert must in pc.HOT_FILES
    # append-only files are a subset of the hot list
    assert set(pc.APPEND_ONLY) <= set(pc.HOT_FILES)


def test_hot_files_exist_in_the_repo():
    """A renamed file would silently stop being watched."""
    missing = [f for f in pc.HOT_FILES if not (REPO / f).exists()]
    assert missing == [], f"watched files no longer exist: {missing}"
