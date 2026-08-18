"""T016b — the automated API-vs-statement diff. The human keeps the final word.

    python scripts/cross_check_schwab.py --start 2026-03-01 --end 2026-03-31

Pulls the window from the Schwab API, parses the statements already sitting in
private/ (T102/T108b), and joins the two: same Eastern trade date, same
instrument, same side, same qty, price within tolerance. API executions are
aggregated per order first — statements are per-order documents, and the
owner's own 71+29 = 100 @ 0.21 check proved that arithmetic to the penny.

Three buckets, printed in full: MATCHED, API-ONLY, STATEMENT-ONLY. Nothing is
silently reconciled; near-misses (one field off) are labelled beneath the
buckets they stay in. Exit 0 = every line found its counterpart. Exit 1 =
something needs your eyes. This replaces none of your tick-offs — it just does
the bookkeeping so your time goes to the lines that disagree.

Read-only (D026): this script cannot place, modify, or cancel anything.
"""

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from analysis.cross_check import cross_check  # noqa: E402
from analysis.market_time import market_window_utc  # noqa: E402
from data.schwab import SchwabClient, SchwabError, map_transactions  # noqa: E402
from data.statements import parse_directory  # noqa: E402
from settings import ConfigError, get_settings  # noqa: E402

# The owner's statements carry rotated watermark text; pypdf logs a warning
# per page ("Rotated text discovered") — 90+ lines of noise before the diff.
# Quieted HERE at the CLI, not in the library: parse failures still surface
# as unparsed entries in the report, which is the signal that matters.
logging.getLogger("pypdf").setLevel(logging.ERROR)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Diff Schwab API fills against statement-parsed fills (T016b).")
    ap.add_argument("--start", required=True, help="YYYY-MM-DD (inclusive)")
    ap.add_argument("--end", required=True, help="YYYY-MM-DD (inclusive)")
    ap.add_argument("--statements", default=str(ROOT / "private" / "statements"),
                    help="folder with statement PDFs (default: private/statements — "
                         "same as autopsy.py/pattern_check.py; not recursive)")
    ap.add_argument("--price-tol", type=float, default=0.01,
                    help="max price difference in dollars (default 0.01)")
    ap.add_argument("--account", default=None, help="last 4 digits, if several")
    args = ap.parse_args()

    try:
        get_settings().require_schwab()
    except ConfigError as e:
        print(f"NOT CONFIGURED\n  {e}")
        return 2

    # Inclusive MARKET days (T016b owner-run fix): midnight-UTC ends silently
    # dropped the final session — his real 3/31 buy looked statement-only.
    start_d = date.fromisoformat(args.start)
    end_d = date.fromisoformat(args.end)
    start, end = market_window_utc(start_d, end_d)

    try:
        with SchwabClient() as client:
            accounts = client.list_accounts()
            if args.account:
                accounts = [a for a in accounts
                            if a.number_masked.endswith(args.account)]
                if not accounts:
                    print(f"No account ending {args.account}.")
                    return 2
            account = accounts[0]
            rows = client.get_transactions(account.hash_value, start, end)
    except SchwabError as e:
        print(f"SCHWAB UNAVAILABLE — no diff performed\n  {e}")
        return 2
    api_report = map_transactions(rows)

    stmt_report = parse_directory(args.statements)
    if stmt_report.files_read == 0:
        # Owner's first run caught this: an empty statement side must NOT be
        # diffed — every API order would print as "API-only", 38 fake problems
        # that are really one missing input. Refuse loudly instead.
        print(f"NO STATEMENT FILES FOUND in {args.statements}\n"
              f"  Nothing to diff against — that folder has no .pdf/.txt files "
              f"(note: not searched recursively).\n"
              f"  Point --statements at the folder that holds your monthly "
              f"statements and daily confirmations.")
        return 2
    window_fills = [f for f in stmt_report.fills
                    if start_d <= f.trade_date <= end_d]
    if not window_fills:
        print(f"Statements parsed ({stmt_report.summary()}) but NONE of their "
              f"fills fall in {args.start} .. {args.end}.\n"
              f"  Nothing to diff — check the window matches the statements "
              f"you have on disk.")
        return 2

    print(f"account {account.number_masked}   window {args.start} .. {args.end}")
    print(f"API: {len(api_report.fills)} executions "
          f"({len(api_report.unmapped)} unmapped — see reconcile_schwab.py)")
    print(f"Statements: {stmt_report.summary()}; {len(window_fills)} fills in window\n")

    report = cross_check(api_report.fills, window_fills, price_tol=args.price_tol)

    print(f"=== MATCHED ({len(report.matched)}) — two sources agree ===")
    for a, s, fee_note in report.matched:
        print(f"  {a.describe()}")
        print(f"    = {s.describe()}   [{fee_note}]")

    print(f"\n=== API-ONLY ({len(report.api_only)}) — in the API, "
          f"no statement line found ===")
    for a in report.api_only:
        print(f"  ! {a.describe()}")
    if not report.api_only:
        print("  none")

    print(f"\n=== STATEMENT-ONLY ({len(report.statement_only)}) — on a "
          f"statement, no API order found ===")
    for s in report.statement_only:
        print(f"  ! {s.describe()}")
    if not report.statement_only:
        print("  none")

    if report.near_misses:
        print(f"\n=== NEAR MISSES ({len(report.near_misses)}) — labelled, "
              f"NOT reconciled; the lines above still count as unmatched ===")
        for n in report.near_misses:
            print(f"  ~ {n}")

    if report.unparseable:
        print(f"\n=== UNPARSEABLE ({len(report.unparseable)}) ===")
        for u in report.unparseable:
            print(f"  ? {u}")

    print(f"\n{report.summary()}")
    if report.clean:
        print("CLEAN — every line on both sides found its counterpart. "
              "Your tick-off remains the final word.")
        return 0
    print("ATTENTION — unmatched or unparseable lines above need your eyes.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
