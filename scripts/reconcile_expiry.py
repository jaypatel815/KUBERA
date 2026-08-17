"""T108 — verify assumed worthless expiries against monthly statements (I026).

The autopsy closes never-sold option lots at exit 0 on their expiry date. This
script checks every one of those ASSUMPTIONS against the explicit Expired /
Assigned / Exercised activity rows on the monthly brokerage statements in the
same folder, and reports, contract by contract, whether the assumption is safe.

Usage:
  python scripts/reconcile_expiry.py                       # private/statements
  python scripts/reconcile_expiry.py --dir private/statements
  python scripts/reconcile_expiry.py --asof 2026-08-17     # deterministic runs
  python scripts/reconcile_expiry.py --json

Exit codes: 0 = every assumption confirmed; 2 = discrepancies to read above.
"""

import argparse
import json
import sys
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from analysis.autopsy import match_fifo_trips, normalize_fill  # noqa: E402
from analysis.expiry_reconcile import (  # noqa: E402
    parse_statement_expirations,
    reconcile,
)
from data.statements import (  # noqa: E402
    extract_pdf_text,
    is_monthly_statement,
    parse_directory,
)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Reconcile assumed option expiries against monthly statements (T108)."
    )
    ap.add_argument("--dir", default=str(ROOT / "private" / "statements"),
                    help="folder holding BOTH confirmations and monthly statements")
    ap.add_argument("--asof", default=None,
                    help="YYYY-MM-DD expiry cutoff (default: today UTC)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    folder = Path(args.dir)
    if not folder.is_dir():
        print(f"Not a directory: {folder}")
        return 2
    asof = date.fromisoformat(args.asof) if args.asof else datetime.now(timezone.utc).date()

    # 1. Confirmations -> fills -> expiry-assumed trips.
    rep = parse_directory(folder)
    fills = [normalize_fill(f) for f in rep.fills]
    trips = match_fifo_trips(fills, asof=asof)
    assumed = [t for t in trips if t.closed_by == "expiry_assumed"]

    # 2. Monthly statements -> explicit removal rows.
    expiries, unparsed, n_statements = [], [], 0
    for p in sorted(folder.iterdir()):
        if p.suffix.lower() != ".pdf":
            continue
        try:
            text = extract_pdf_text(p)
        except Exception as e:  # noqa: BLE001 — report the file, keep reconciling
            unparsed.append({"file": p.name, "why": f"PDF extraction failed ({e})"})
            continue
        if not is_monthly_statement(text, p.name):
            continue
        n_statements += 1
        found, bad = parse_statement_expirations(text, source_file=p.name)
        expiries.extend(found)
        unparsed.extend(bad)

    result = reconcile(assumed, expiries,
                       statement_unparsed=unparsed, statements_read=n_statements)

    if args.json:
        print(json.dumps({
            "asof": asof.isoformat(),
            "confirmations": rep.summary(),
            "statements_read": result.statements_read,
            "entries": [asdict(e) for e in result.entries],
            "unparsed": result.unparsed,
            "clean": result.clean,
            "note": result.note,
        }, indent=2, default=str))
        return 0 if result.clean else 2

    print("=" * 74)
    print("        T108 EXPIRY RECONCILIATION — assumptions vs monthly statements")
    print("=" * 74)
    print(f"  As of                  : {asof.isoformat()}")
    print(f"  Confirmations parsed   : {rep.summary()}")
    print(f"  Monthly statements read: {result.statements_read}")
    print(f"  Assumed-expiry trips   : {len(assumed)} "
          f"(${sum(t.pnl for t in assumed):,.2f} at exit 0)")
    print()
    print(f"  confirmed_expired        : {result.confirmed}")
    print(f"  quantity_mismatch        : {result.quantity_mismatches}")
    print(f"  not_in_statements        : {result.not_in_statements}")
    print(f"  no_confirmation_coverage : {result.no_confirmation_coverage}")
    print(f"  assigned_or_exercised    : {result.assigned_or_exercised}")
    print()
    for e in result.entries:
        mark = "OK " if e.status == "confirmed_expired" else "!! "
        print(f"  {mark}{e.symbol:<5} {e.expiry} {e.strike:g}{e.right[:1].upper()} "
              f"assumed={e.assumed_qty:g} (${e.assumed_pnl:,.2f})  "
              f"statement={e.statement_qty:g} {e.statement_action}  [{e.status}]")
        if e.status != "confirmed_expired":
            print(f"      {e.detail}")
    if result.unparsed:
        print()
        print("  UNPARSED statement rows (never guessed, always listed):")
        for u in result.unparsed:
            print(f"    {u.get('file','?')}: {u.get('why','?')}")
    print()
    print("  " + ("CLEAN — every exit-0 assumption is confirmed by a statement."
                  if result.clean else
                  "DISCREPANCIES — read the flagged lines before trusting any "
                  "autopsy or pattern number."))
    print("=" * 74)
    return 0 if result.clean else 2


if __name__ == "__main__":
    sys.exit(main())
