"""T016 acceptance: does the import match the statement? (D026)

Run this BEFORE trusting anything KUBERA says about your trading behaviour.

    python scripts/reconcile_schwab.py --start 2026-03-01 --end 2026-03-31

The whole ticket rests on one claim: that the fills KUBERA imported are the
trades you actually made. That claim is cheap to assert and easy to get subtly
wrong — a timezone that shifts a trade across a day boundary, an options leg
silently skipped, a partial fill counted once instead of twice. None of those
crash. They just quietly change every conclusion downstream: your median hold,
your win rate by bucket, whether you size up after losses.

So this script prints what was imported in a form you can hold next to your
Schwab statement and tick off line by line. It deliberately does NOT try to
parse the statement and declare victory itself — a machine agreeing with itself
is not verification. You are the check.

It also prints, loudly, everything the mapper could NOT interpret. A row KUBERA
cannot explain is not allowed to vanish; if your statement shows 41 trades and
this shows 38 mapped plus 3 unmapped, that reconciles. 38 with nothing else said
would not.

Read-only: this script cannot place, modify or cancel anything (D026).
"""

import argparse
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from data.schwab import SchwabClient, map_transactions  # noqa: E402
from settings import ConfigError, get_settings  # noqa: E402


def _day(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def main() -> int:
    ap = argparse.ArgumentParser(description="Reconcile Schwab imports against a statement.")
    ap.add_argument("--start", required=True, help="YYYY-MM-DD (inclusive)")
    ap.add_argument("--end", required=True, help="YYYY-MM-DD (inclusive)")
    ap.add_argument("--account", default=None, help="last 4 digits, if several accounts")
    args = ap.parse_args()

    try:
        get_settings().require_schwab()
    except ConfigError as e:
        print(f"NOT CONFIGURED\n  {e}")
        return 2

    start, end = _day(args.start), _day(args.end)

    with SchwabClient() as client:
        accounts = client.list_accounts()
        if args.account:
            accounts = [a for a in accounts if a.number_masked.endswith(args.account)]
            if not accounts:
                print(f"No account ending {args.account}. Found: "
                      f"{', '.join(a.number_masked for a in accounts)}")
                return 2
        account = accounts[0]
        print(f"account {account.number_masked}   window {args.start} .. {args.end}\n")

        rows = client.get_transactions(account.hash_value, start, end)

    report = map_transactions(rows)
    print(report.summary())
    print()

    # Per-day, per-symbol — the shape a statement is actually organised in, so
    # the comparison is a scan rather than a puzzle.
    by_day: dict[str, list] = defaultdict(list)
    for f in report.fills:
        by_day[f.occurred_at.date().isoformat()].append(f)

    print("IMPORTED FILLS — tick these against your statement")
    print("-" * 66)
    for day in sorted(by_day):
        print(f"  {day}")
        for f in sorted(by_day[day], key=lambda x: (x.symbol, x.occurred_at)):
            print(f"    {f.side.upper():4}  {f.qty:>10,.4f}  {f.symbol:<6} "
                  f"@ {f.price:>10,.4f}   {f.occurred_at.time().isoformat(timespec='seconds')}")
    if not by_day:
        print("  (none)")

    if report.cash:
        print("\nCASH MOVEMENTS")
        print("-" * 66)
        for c in sorted(report.cash, key=lambda x: x.occurred_at):
            print(f"  {c.occurred_at.date().isoformat()}  {c.kind:<10} {c.amount:>12,.2f}")

    if report.unmapped:
        print("\nUNMAPPED — these are NOT in your imported history")
        print("-" * 66)
        print("  Every one needs an explanation before the import is trusted.")
        print("  Options, corporate actions and dividends are expected here;")
        print("  a plain equity trade is NOT, and means the mapper needs work.")
        for u in report.unmapped:
            print(f"    {u}")

    total_buy = sum(f.qty * f.price for f in report.fills if f.side == "buy")
    total_sell = sum(f.qty * f.price for f in report.fills if f.side == "sell")
    print("\nTOTALS (compare against the statement's activity summary)")
    print("-" * 66)
    print(f"  buys  {total_buy:>14,.2f}")
    print(f"  sells {total_sell:>14,.2f}")
    print(f"  net   {total_sell - total_buy:>14,.2f}   (excludes fees and cash movements)")

    print("\nNEXT: if every line ties out, record it in project-memory/TASKS.md")
    print("under T016 — that reconciliation IS the ticket's acceptance criterion,")
    print("and T103 (the trading autopsy) stays blocked until it passes.")
    return 0 if not report.unmapped else 1


if __name__ == "__main__":
    sys.exit(main())
