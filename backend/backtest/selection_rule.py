"""T109 — the pre-registered selection rule, loaded as a versioned artifact (D029).

The rule that decides whether a strategy earns promotion must exist BEFORE the
experiment whose fate it decides, and the run must record which version of the
rule judged it. Otherwise the standard drifts to fit the result — the failure
mode D029 adopted this against: a near-miss is a miss, and the rule does not
move after the result is known.

This module does exactly one thing: load docs/SELECTION_RULE.md, extract its
version line, and refuse loudly when the file is missing or unversioned. The
gates themselves stay where they always were — enforced in code
(backtest/stats.walk_forward, backtest/ledger.is_promoted) — the document is
the pre-registered, human-readable statement of that standard, and the version
string is what gets stamped onto every promotion run.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# docs/SELECTION_RULE.md relative to the repo root (two levels above backend/).
_DEFAULT_PATH = Path(__file__).resolve().parents[2] / "docs" / "SELECTION_RULE.md"

# Matches "Version: v1" and "Version: v1 (2026-08-17)" — the token is the
# version, anything after it is annotation.
_VERSION_LINE = re.compile(r"^Version:\s*(?P<version>\S+)(?:\s+.*)?$", re.MULTILINE)


@dataclass(frozen=True)
class SelectionRule:
    version: str
    path: str
    text: str


class SelectionRuleMissing(RuntimeError):
    """Raised when promotion is attempted without a pre-registered rule."""


def load_selection_rule(path: str | Path | None = None) -> SelectionRule:
    """Load and version-check the pre-registered selection rule.

    Refuses (raises SelectionRuleMissing) when the file is absent or carries no
    version line — promoting against an unwritten or unversioned standard is
    exactly what pre-registration exists to prevent, so there is no fallback.
    """
    p = Path(path) if path is not None else _DEFAULT_PATH
    if not p.exists():
        raise SelectionRuleMissing(
            f"pre-registered selection rule not found at {p} — promotion is "
            "refused without one (D029). Restore docs/SELECTION_RULE.md from "
            "git; do not improvise a standard after seeing results."
        )
    text = p.read_text(encoding="utf-8")
    m = _VERSION_LINE.search(text)
    if not m:
        raise SelectionRuleMissing(
            f"{p} has no 'Version:' line — an unversioned rule cannot be "
            "cited by a promotion record (D029). Add 'Version: vN (YYYY-MM-DD)' "
            "near the top."
        )
    return SelectionRule(version=m.group("version"), path=str(p), text=text)
