"""T128 — the runbook cannot rot: every script it names must exist, and the
incidents the spec asked for by name must be covered. A runbook pointing at
a deleted script is worse than none — it burns trust mid-incident."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNBOOK = ROOT / "docs" / "RUNBOOK.md"


def test_every_named_script_exists():
    text = RUNBOOK.read_text(encoding="utf-8")
    names = set(re.findall(r"scripts[/\\](\w+\.py)", text))
    assert len(names) >= 12  # the runbook actually covers the ops surface
    missing = sorted(n for n in names if not (ROOT / "scripts" / n).exists())
    assert missing == [], f"runbook names scripts that do not exist: {missing}"


def test_spec_named_incidents_are_covered():
    text = RUNBOOK.read_text(encoding="utf-8")
    # PROJECT_SPEC Phase 8 names these two incidents verbatim
    assert "data feed is down" in text
    assert "circuit breaker" in text
    # and the runbook keeps the house exit-code convention on the record
    assert "0 = healthy" in text and "2 = not configured" in text
    # no secrets guidance without the never-paste rule
    assert "Names and lengths only" in text
