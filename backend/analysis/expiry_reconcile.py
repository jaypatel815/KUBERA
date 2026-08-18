"""T108 — reconcile ASSUMED worthless expiries against monthly statements (I026).

The expiry-aware matcher (analysis/autopsy.py) closes never-sold option lots at
exit 0 on their expiry date. That is an ASSUMPTION: an in-the-money lot would
have been auto-exercised or assigned, not expired worthless, and exit 0 would
then be wrong. Monthly brokerage statements record what actually happened —
every removal appears as an explicit "Expired" (or, in principle, "Assigned" /
"Exercised") activity row. This module parses those rows and cross-checks each
assumed closure against them.

The row formats are built from the owner's five REAL statements (Jan–May 2026,
twelve expiration events), not a guessed layout — the T102 lesson. Three
variants observed, all with the quantity in accounting parentheses:

    Other  Expired  Short  SPY  05/11/2026  PUT  ...$733     (135.0000)
           Activity        733.00  P        EXP  05/11/26

    05/18  Other  Expired  Short  AMD  05/15/2026  CALL  ...$490   (1.0000)
           Activity              490.00  C   EXP  05/15/26

    05/26  Other  Expired  Short  NVDA        CALL  ...$285  EXP   (1.0000)
           Activity              05/22/2026   05/22/26
                                 285.00  C

"Short" is the tax-lot TERM (short-term), not a short position: in every
observed case the purchases sit directly above the removal. The expiry date and
the clean "STRIKE.XX P/C" pair land on the action line or one of the next two
lines, and those continuation lines can belong to the NEXT transaction — so the
window search refuses lines that start a new transaction rather than grabbing a
neighbouring contract's date.

DO NOT KEY ON THE "EXP" TOKEN (owner clarification, 2026-08-17): "EXP MM/DD/YY"
is the label for the contract's EXPIRATION DATE and appears on EVERY option
row — ordinary purchases and sales included. The signal for a worthless expiry
is the ACTION word "Expired" (with a parenthesised removal quantity), which is
exactly what _ACTION matches. Matching "EXP" instead would misread every option
purchase as an expiration. Mechanical proof of the current reading: the T108
reconciliation matched all 13 expired contracts against these action rows,
quantity-exact.

Anything unparseable is REPORTED, never guessed — the same rule as the
confirmation parser, for the same reason.

Pure functions; file I/O lives in scripts/reconcile_expiry.py.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Sequence

from analysis.autopsy import AutopsyRoundTrip

_ACTION = re.compile(r"\b(?P<action>Expired|Assigned|Exercised)\b")
_QTY = re.compile(r"\((?P<qty>[\d,]+(?:\.\d+)?)\)")
_RIGHT_WORD = re.compile(r"\b(?P<right>PUT|CALL)\b")
_FULL_DATE = re.compile(r"\b(\d{2}/\d{2}/\d{4})\b")
# "733.00  P" on a continuation line — the reliable strike source. The "$733"
# fragment on the action line is glued into a truncated description column
# ("SPDR   S&$733") and drops decimals, so it is used for nothing.
_STRIKE_CONT = re.compile(r"\b(?P<strike>\d{1,6}(?:,\d{3})*\.\d{2})\s+(?P<letter>[PC])\b")
# Lines that begin a different transaction — their dates/strikes belong to some
# OTHER contract and must never be read as this row's continuation.
_NEW_TRANSACTION = re.compile(r"\b(Purchase|Sale|Expense|Bought|Sold)\b")

# Matching tolerance for strikes parsed from two different documents.
_STRIKE_TOL = 0.005


@dataclass(frozen=True)
class StatementExpiry:
    """One explicit option-removal activity row from a monthly statement."""

    symbol: str
    expiry: date
    right: str                 # "put" | "call"
    strike: float
    qty: float
    action: str                # "expired" | "assigned" | "exercised"
    source_file: str = ""
    line_no: int = 0

    @property
    def contract_key(self) -> str:
        """Same shape as AutopsyFill.contract_key so the two sides join —
        including the right as the FULL word (PUT/CALL), which is what
        AutopsyFill embeds. The first cut of this used the single letter and
        every join silently missed (caught on the real statements)."""
        return f"{self.symbol}_{self.expiry.isoformat()}_{self.strike}_{self.right.upper()}"


@dataclass(frozen=True)
class ReconcileEntry:
    contract_key: str
    symbol: str
    expiry: str
    right: str
    strike: float
    assumed_qty: float          # contracts closed at exit 0 by the matcher
    assumed_pnl: float
    statement_qty: float        # contracts the statement says were removed
    statement_action: str       # "expired" / "assigned" / "exercised" / ""
    status: str
    detail: str


@dataclass(frozen=True)
class ExpiryReconciliation:
    entries: list[ReconcileEntry] = field(default_factory=list)
    unparsed: list[dict] = field(default_factory=list)
    statements_read: int = 0
    confirmed: int = 0
    quantity_mismatches: int = 0
    not_in_statements: int = 0
    no_confirmation_coverage: int = 0
    assigned_or_exercised: int = 0
    note: str = (
        "Cross-check of assumed worthless expiries (exit 0, T108) against the explicit "
        "Expired/Assigned/Exercised activity rows on monthly brokerage statements. "
        "Anything other than 'confirmed_expired' means the assumption is not yet safe "
        "to trust for that contract."
    )

    @property
    def clean(self) -> bool:
        # no_confirmation_coverage counts too: a loss the statement records but
        # the confirmations never saw is a MISSING loss, which is the exact
        # failure class this whole ticket exists to end. (The first cut of this
        # property omitted it; the test caught the omission.)
        return (
            self.quantity_mismatches == 0
            and self.not_in_statements == 0
            and self.no_confirmation_coverage == 0
            and self.assigned_or_exercised == 0
            and not self.unparsed
        )


def _continuation_lines(lines: list[str], i: int) -> list[str]:
    """Up to two lines after i that do NOT start a different transaction."""
    out: list[str] = []
    for j in (i + 1, i + 2):
        if j >= len(lines):
            break
        if _NEW_TRANSACTION.search(lines[j]):
            break
        out.append(lines[j])
    return out


def parse_statement_expirations(
    text: str, source_file: str = ""
) -> tuple[list[StatementExpiry], list[dict]]:
    """Extract every option-removal activity row from one statement's text layer."""
    lines = text.splitlines()
    found: list[StatementExpiry] = []
    unparsed: list[dict] = []

    for i, line in enumerate(lines):
        am = _ACTION.search(line)
        qm = _QTY.search(line)
        if not am or not qm:
            continue  # an action word without a parenthesised qty is prose, not a row

        window = [line[am.end():]] + _continuation_lines(lines, i)

        # Symbol: first 1–6 letter uppercase token after the action word that is
        # not the tax-term column. Observed rows put it immediately after "Short".
        symbol = ""
        for tok in line[am.end():].split():
            if tok in {"Short", "Long", "Activity"}:
                continue
            if re.fullmatch(r"[A-Z]{1,6}", tok):
                symbol = tok
            break

        expiry: date | None = None
        for chunk in window:
            dm = _FULL_DATE.search(chunk)
            if dm:
                try:
                    expiry = datetime.strptime(dm.group(1), "%m/%d/%Y").date()
                except ValueError:
                    expiry = None
                break

        right = ""
        rm = _RIGHT_WORD.search(line)
        if rm:
            right = rm.group("right").lower()

        strike: float | None = None
        letter = ""
        for chunk in window:
            sm = _STRIKE_CONT.search(chunk)
            if sm:
                strike = float(sm.group("strike").replace(",", ""))
                letter = sm.group("letter")
                break
        if not right and letter:
            right = "put" if letter == "P" else "call"

        missing = [
            name
            for name, ok in (
                ("symbol", bool(symbol)),
                ("expiry date", expiry is not None),
                ("right", bool(right)),
                ("strike", strike is not None),
            )
            if not ok
        ]
        if missing:
            unparsed.append({
                "file": source_file,
                "line_no": i,
                "why": f"{am.group('action')} row missing {', '.join(missing)} — refusing to guess",
            })
            continue
        if letter and right and letter != right[0].upper():
            unparsed.append({
                "file": source_file,
                "line_no": i,
                "why": f"right mismatch: line says {right.upper()}, "
                       f"strike continuation says {letter} — refusing to guess",
            })
            continue

        assert expiry is not None and strike is not None  # narrowed above
        found.append(StatementExpiry(
            symbol=symbol,
            expiry=expiry,
            right=right,
            strike=strike,
            qty=float(qm.group("qty").replace(",", "")),
            action=am.group("action").lower(),
            source_file=source_file,
            line_no=i,
        ))

    return found, unparsed


def _keys_match(trip_key: str, stmt: StatementExpiry) -> bool:
    """Trip keys embed the strike with float repr; compare piecewise with tolerance."""
    parts = trip_key.rsplit("_", 3)
    if len(parts) != 4:
        return False
    sym, expiry_iso, strike_s, right_token = parts
    # Trip keys embed the right as the full word ("PUT"/"CALL"); accept the
    # single letter too so a future key-shape change fails toward matching
    # by first letter rather than silently never joining.
    if sym != stmt.symbol or not right_token or right_token[0] != stmt.right[0].upper():
        return False
    if expiry_iso != stmt.expiry.isoformat():
        return False
    try:
        return abs(float(strike_s) - stmt.strike) <= _STRIKE_TOL
    except ValueError:
        return False


def reconcile(
    assumed_trips: Sequence[AutopsyRoundTrip],
    statement_expiries: Sequence[StatementExpiry],
    statement_unparsed: Sequence[dict] = (),
    statements_read: int = 0,
) -> ExpiryReconciliation:
    """Join assumed closures against statement removal rows, contract by contract."""
    by_key: dict[str, dict] = {}
    for t in assumed_trips:
        if t.closed_by != "expiry_assumed":
            continue
        slot = by_key.setdefault(t.contract_key, {
            "symbol": t.symbol, "qty": 0.0, "pnl": 0.0,
            "expiry": "", "right": "", "strike": 0.0,
        })
        slot["qty"] += t.qty
        slot["pnl"] = round(slot["pnl"] + t.pnl, 2)
        parts = t.contract_key.rsplit("_", 3)
        if len(parts) == 4:
            slot["expiry"] = parts[1]
            slot["strike"] = float(parts[2]) if parts[2] else 0.0
            slot["right"] = {"P": "put", "C": "call", "PUT": "put", "CALL": "call"}.get(
                parts[3], parts[3].lower()
            )

    entries: list[ReconcileEntry] = []
    matched_stmt: set[int] = set()
    counts = {"confirmed": 0, "qty": 0, "missing": 0, "coverage": 0, "assigned": 0}

    for key, slot in sorted(by_key.items()):
        match: StatementExpiry | None = None
        for idx, se in enumerate(statement_expiries):
            if idx not in matched_stmt and _keys_match(key, se):
                match = se
                matched_stmt.add(idx)
                break

        if match is None:
            counts["missing"] += 1
            status, action, stmt_qty = "not_in_statements", "", 0.0
            detail = (
                "no statement row covers this contract — either the month's statement "
                "is missing from the folder, or the removal happened another way. "
                "Exit 0 is UNVERIFIED here."
            )
        elif match.action != "expired":
            counts["assigned"] += 1
            status, action, stmt_qty = "assigned_or_exercised", match.action, match.qty
            detail = (
                f"statement says {match.action.upper()}, not expired — exit 0 is WRONG "
                "for this lot; the true exit is the exercise/assignment economics. "
                "Correct this trip manually before trusting totals."
            )
        elif abs(match.qty - slot["qty"]) <= 1e-6:
            counts["confirmed"] += 1
            status, action, stmt_qty = "confirmed_expired", match.action, match.qty
            detail = "statement confirms worthless expiry of the exact quantity."
        else:
            counts["qty"] += 1
            status, action, stmt_qty = "quantity_mismatch", match.action, match.qty
            detail = (
                f"statement removed {match.qty:g} contracts but confirmations only "
                f"account for {slot['qty']:g} — most likely one or more confirmation "
                "PDFs are missing from the folder, so realized losses are UNDERSTATED "
                "even after the expiry fix."
            )

        entries.append(ReconcileEntry(
            contract_key=key, symbol=slot["symbol"], expiry=slot["expiry"],
            right=slot["right"], strike=slot["strike"],
            assumed_qty=round(slot["qty"], 4), assumed_pnl=slot["pnl"],
            statement_qty=stmt_qty, statement_action=action,
            status=status, detail=detail,
        ))

    for idx, se in enumerate(statement_expiries):
        if idx in matched_stmt:
            continue
        counts["coverage"] += 1
        entries.append(ReconcileEntry(
            contract_key=se.contract_key, symbol=se.symbol,
            expiry=se.expiry.isoformat(), right=se.right, strike=se.strike,
            assumed_qty=0.0, assumed_pnl=0.0,
            statement_qty=se.qty, statement_action=se.action,
            status="no_confirmation_coverage",
            detail=(
                f"statement records {se.qty:g} contract(s) {se.action} but the "
                "confirmations never showed the purchase — this loss is invisible to "
                "the autopsy entirely and its premium must be added from the statement."
            ),
        ))

    return ExpiryReconciliation(
        entries=entries,
        unparsed=list(statement_unparsed),
        statements_read=statements_read,
        confirmed=counts["confirmed"],
        quantity_mismatches=counts["qty"],
        not_in_statements=counts["missing"],
        no_confirmation_coverage=counts["coverage"],
        assigned_or_exercised=counts["assigned"],
    )
