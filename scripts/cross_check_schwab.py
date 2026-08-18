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
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from analysis.cross_check import cross_check  # noqa: E402
from data.schwab import SchwabClient, SchwabError, map_transactions  # noqa: E402
from data.statements import parse_directory  # noqa: E402
from settings import ConfigError, get_settings  # noqa: E402


def _day(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Diff Schwab API fills against statement-parsed fills (T016b).")
    ap.add_argument("--start", required=True, help="YYYY-MM-DD (inclusive)")
    ap.add_argument("--end", required=True, help="YYYY-MM-DD (inclusive)")
    ap.add_argument("--statements", default=str(ROOT / "private"),
                    help="folder with statement PDFs (default: private/)")
    ap.add_argument("--price-tol", type=float, default=0.01,
                    help="max price difference in dollars (default 0.01)")
    ap.add_argument("--account", default=None, help="last 4 digits, if several")
    args = ap.parse_args()

    try:
        get_settings().require_schwab()
    except ConfigError as e:
        print(f"NOT CONFIGURED\n  {e}")
        return 2

    start, end = _day(args.start), _day(args.end)

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
    window_fills = [f for f in stmt_report.fills
                    if start.date() <= f.trade_date <= end.date()]

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
