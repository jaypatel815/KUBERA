"""I029 — print the REAL shape of Schwab transaction rows. Run on your machine:

    python scripts\\schwab_probe_shape.py --start 2026-03-01 --end 2026-03-31

Your reconciliation caught two mapping defects: dates that don't match when
you traded, and expirations presented as sales. The unit-test fixtures follow
Schwab's PUBLISHED shapes; your live rows evidently differ, and the T102 rule
is that parsers get fixed against OBSERVED rows, never guesses. This prints
what the API actually sends so the mapper can be corrected against reality.

What it prints (and what it hides):
- Any key whose name contains 'account' is STRIPPED from every row.
- For each row: type, status, and EVERY field whose name contains
  date/time/expir + its value — this settles the date question.
- For TRADE rows (3 sample days) and for EVERY row that looks like an option
  EXPIRATION (zero-priced legs, RECEIVE_AND_DELIVER, description mentioning
  expiry): the full transferItems structure — this settles the expiry
  question.
Everything else (dollar amounts on unrelated rows) is summarised, not dumped.

Paste the output to any KUBERA agent. It stays on your machine until you do.
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from data.schwab import SchwabClient  # noqa: E402
from settings import ConfigError  # noqa: E402


def _strip_account(obj):
    """Remove any key containing 'account', recursively."""
    if isinstance(obj, dict):
        return {k: _strip_account(v) for k, v in obj.items()
                if "account" not in k.lower()}
    if isinstance(obj, list):
        return [_strip_account(v) for v in obj]
    return obj


def _strip_account_row(row: dict) -> dict:
    """Typed top-level wrapper: a transaction row is a dict in, a dict out."""
    return {k: _strip_account(v) for k, v in row.items()
            if "account" not in k.lower()}


def _datey_fields(row: dict) -> dict:
    return {k: v for k, v in row.items()
            if any(t in k.lower() for t in ("date", "time", "expir"))}


def _looks_like_expiration(row: dict) -> bool:
    kind = str(row.get("type", "")).upper()
    if "RECEIVE" in kind or "DELIVER" in kind or "EXPIR" in kind:
        return True
    text = json.dumps(row).lower()
    if "expir" in text:
        return True
    for item in row.get("transferItems", []) or []:
        inst = item.get("instrument") or {}
        if inst.get("assetType") == "OPTION" and not item.get("price"):
            return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description="Print real Schwab row shapes (I029).")
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    args = ap.parse_args()

    def day(t):
        return datetime.strptime(t, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    try:
        with SchwabClient() as c:
            accounts = c.list_accounts()
            rows = c.get_transactions(accounts[0].hash_value,
                                      day(args.start), day(args.end))
    except ConfigError as e:
        print(e)
        return 2

    rows = [_strip_account_row(r) for r in rows]
    print(f"{len(rows)} raw transactions {args.start}..{args.end}\n")

    by_type = defaultdict(list)
    for r in rows:
        by_type[str(r.get("type", "?")).upper()].append(r)
    print("row types:", {k: len(v) for k, v in sorted(by_type.items())}, "\n")

    print("=" * 74)
    print("DATE/TIME FIELDS ON EVERY ROW (the date-shift question)")
    print("=" * 74)
    for r in rows:
        rid = str(r.get("activityId") or r.get("transactionId") or "?")[-6:]
        print(f"  #{rid} {str(r.get('type', '?')):<20}", _datey_fields(r))

    print()
    print("=" * 74)
    print("FULL SHAPE — first 3 distinct trade days' TRADE rows")
    print("=" * 74)
    days_seen: set[str] = set()
    for r in by_type.get("TRADE", []):
        d = str(_datey_fields(r).get("time") or _datey_fields(r).get("tradeDate") or "")[:10]
        if d not in days_seen and len(days_seen) >= 3:
            continue
        days_seen.add(d)
        print(json.dumps(r, indent=1, default=str)[:1400])
        print("-" * 74)

    print()
    print("=" * 74)
    print("FULL SHAPE — every row that looks like an option EXPIRATION")
    print("=" * 74)
    hits = 0
    for r in rows:
        if _looks_like_expiration(r):
            hits += 1
            print(json.dumps(r, indent=1, default=str)[:1400])
            print("-" * 74)
    if not hits:
        print("  (none matched the expiration heuristics — paste the DATE table")
        print("   above plus one TRADE row and say which symbol expired; the row")
        print("   for it is in there under some other type.)")

    print("\nPaste everything above to any KUBERA agent — the mapper gets fixed")
    print("against these observed shapes, then reconcile_schwab.py runs again.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
