"""T156 (D039 Phase 9) — CSV spending import: card exports → categorized
spending_entries, idempotently.

Doctrine, applied to bank files:
- The rule map is OWNER-EDITED JSON (substring → category). Unknown
  merchants land in "uncategorized" and are REPORTED so the owner can
  extend the map — categories are never guessed.
- Idempotent by import_key: re-importing the same file, or an overlapping
  newer export, writes nothing twice. Genuine same-day duplicates (two
  identical coffees) survive via an occurrence ordinal.
- Sign conventions differ by bank. This module never flips signs on its
  own: `negate=True` is the owner's statement that his export writes
  charges as negatives. When most amounts are negative WITHOUT negate,
  the report says so loudly instead of guessing.
- Credits/payments (non-positive after normalization) are skipped and
  counted — a card payment is not spending.
- Unparseable rows are counted with their reason, never invented.
"""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from data.household import HouseholdError, log_spending

DATE_HEADERS = ("transaction date", "trans date", "trans. date", "date",
                "posted date", "posting date", "post date")
AMOUNT_HEADERS = ("amount", "transaction amount", "amount (usd)")
DEBIT_HEADER, CREDIT_HEADER = "debit", "credit"
DESC_HEADERS = ("description", "merchant", "merchant name", "payee",
                "details", "memo")

STARTER_RULES = {
    "_comment": ("substring (lowercased) -> category. First edit this file, "
                 "then re-run the import — unmatched descriptions are listed "
                 "in every report. Longest matching substring wins."),
    "kroger": "groceries",
    "walmart": "groceries",
    "costco": "groceries",
    "shell": "gas",
    "chevron": "gas",
    "netflix": "subscriptions",
    "spotify": "subscriptions",
    "doordash": "dining",
    "chipotle": "dining",
    "amazon": "shopping",
}


class SpendingImportError(ValueError):
    """Named refusal — unusable files or rule maps never half-import."""


@dataclass
class ImportReport:
    path: str
    total_rows: int = 0
    imported: int = 0
    duplicates_skipped: int = 0
    credits_skipped: int = 0
    unparsed: list[str] = field(default_factory=list)  # "row N: reason"
    uncategorized: int = 0
    unmatched_descriptions: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"{self.path}: {self.imported} imported, "
            f"{self.duplicates_skipped} duplicates, "
            f"{self.credits_skipped} credits/payments skipped, "
            f"{len(self.unparsed)} unparsed, of {self.total_rows} rows",
        ]
        if self.uncategorized:
            top = sorted(self.unmatched_descriptions.items(),
                         key=lambda kv: -kv[1])[:5]
            lines.append(
                f"  {self.uncategorized} uncategorized — extend the rule map "
                "for: " + "; ".join(f"{d!r} x{n}" for d, n in top))
        lines.extend(f"  UNPARSED {u}" for u in self.unparsed[:5])
        lines.extend(f"  WARNING: {w}" for w in self.warnings)
        return "\n".join(lines)


def load_rules(path: Path) -> dict[str, str]:
    """Owner-edited JSON arrives hostile: BOM, wrong shapes. Refuse loudly."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        raise SpendingImportError(
            f"rule map {path} is not valid JSON: {e}") from None
    if not isinstance(raw, dict):
        raise SpendingImportError(
            f"rule map {path} must be a JSON object of "
            "substring -> category")
    return {str(k).strip().lower(): str(v).strip().lower()
            for k, v in raw.items()
            if not str(k).startswith("_") and str(v).strip()}


def write_starter_rules(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(STARTER_RULES, indent=2) + "\n",
                    encoding="utf-8")


def categorize(description: str, rules: dict[str, str]) -> str | None:
    """Longest matching substring wins; ties break alphabetically so the
    result never depends on dict order. None = no rule matched."""
    d = description.lower()
    hits = [k for k in rules if k in d]
    if not hits:
        return None
    best = sorted(hits, key=lambda k: (-len(k), k))[0]
    return rules[best]


def _parse_date(raw: str) -> str:
    raw = raw.strip()
    for fmt in ("%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            pass
    return date.fromisoformat(raw).isoformat()  # raises ValueError if not ISO


def _parse_amount(raw: str) -> float:
    return float(raw.strip().replace("$", "").replace(",", ""))


def _find_columns(headers: list[str]) -> tuple[str, str | None, str]:
    """Return (date_col, amount_col_or_None_for_debit_credit, desc_col).
    Refuses files whose columns cannot be identified — named, not guessed."""
    lower = {h.strip().lower(): h for h in headers}
    date_col = next((lower[c] for c in DATE_HEADERS if c in lower), None)
    desc_col = next((lower[c] for c in DESC_HEADERS if c in lower), None)
    amount_col = next((lower[c] for c in AMOUNT_HEADERS if c in lower), None)
    has_debit_credit = DEBIT_HEADER in lower and CREDIT_HEADER in lower
    if date_col is None or desc_col is None or (
            amount_col is None and not has_debit_credit):
        raise SpendingImportError(
            "cannot identify columns in header "
            f"{headers} — need a date ({'/'.join(DATE_HEADERS[:3])}…), a "
            f"description ({'/'.join(DESC_HEADERS[:3])}…), and an amount "
            f"(or debit+credit pair)")
    return date_col, amount_col, desc_col


def import_csv(session: Session, path: Path, rules: dict[str, str], *,
               negate: bool = False) -> ImportReport:
    report = ImportReport(path=str(path))
    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames:
            raise SpendingImportError(f"{path} has no header row")
        date_col, amount_col, desc_col = _find_columns(list(reader.fieldnames))
        lower = {h.strip().lower(): h for h in reader.fieldnames}

        seen_ordinal: dict[tuple[str, str, str], int] = {}
        negative_amounts = 0
        parsed = 0
        for i, row in enumerate(reader, start=2):  # header is line 1
            report.total_rows += 1
            try:
                day = _parse_date(row[date_col] or "")
                desc = " ".join((row[desc_col] or "").split())
                if amount_col is not None:
                    amount = _parse_amount(row[amount_col] or "")
                else:
                    debit = (row[lower[DEBIT_HEADER]] or "").strip()
                    credit = (row[lower[CREDIT_HEADER]] or "").strip()
                    amount = (_parse_amount(debit) if debit
                              else -_parse_amount(credit))
            except (ValueError, KeyError) as e:
                report.unparsed.append(f"row {i}: {e}")
                continue
            parsed += 1
            if amount < 0:
                negative_amounts += 1
            if negate:
                amount = -amount
            if amount <= 0:
                report.credits_skipped += 1
                continue
            triple = (day, f"{amount:.2f}", desc.lower())
            ordinal = seen_ordinal.get(triple, 0)
            seen_ordinal[triple] = ordinal + 1
            key = hashlib.sha1(
                "|".join((*triple, str(ordinal))).encode()).hexdigest()
            cat = categorize(desc, rules)
            try:
                stored = log_spending(
                    session, amount=round(amount, 2),
                    category=cat or "uncategorized", on=day,
                    note=desc[:200] or None, source="csv", import_key=key)
            except HouseholdError as e:
                report.unparsed.append(f"row {i}: {e}")
                continue
            if stored is None:
                report.duplicates_skipped += 1
            else:
                report.imported += 1
                if cat is None:  # counted only for rows actually stored
                    report.uncategorized += 1
                    report.unmatched_descriptions[desc] = (
                        report.unmatched_descriptions.get(desc, 0) + 1)

        if not negate and parsed and negative_amounts / parsed > 0.6:
            report.warnings.append(
                f"{negative_amounts} of {parsed} amounts are negative — if "
                "this export writes CHARGES as negatives, re-run with "
                "--negate; nothing was flipped automatically")
    return report
