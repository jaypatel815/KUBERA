"""T023 — probe what YOUR FMP tier can actually do. Run on your machine:

    python scripts\\fmp_check.py

The owner reports the FREE tier (no earnings-call transcripts). D026's rule is
verify-before-trust, so before T023 integrates anything, this probes the exact
endpoints the ticket cares about and prints a table of what answered. Paste
that table to any agent; the T023 source decision reads from it.

Prints STATUSES AND COUNTS ONLY — never the key, never response bodies (a
snippet of the error message is shown for paywall/limit classification, with
the key stripped if it were ever echoed).

The sandbox cannot reach financialmodelingprep.com (proxy 403) — this script
exists because the check must run where the key lives.
"""

import re
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]

# What T023 actually needs, one probe each. (path, params, why-it-matters)
# FMP has both /api/v3 and newer /stable paths; both families are probed where
# they differ, because tier gating has historically differed between them too.
PROBES = [
    ("profile", "/stable/profile", {"symbol": "AAPL"},
     "basic access sanity check"),
    ("earnings calendar", "/stable/earnings-calendar", {},
     "T083 event base rates + T076b earnings dates — the biggest unlock"),
    ("earnings calendar (v3)", "/api/v3/earning_calendar", {},
     "legacy path of the same; sometimes gated differently"),
    ("income statement", "/stable/income-statement", {"symbol": "AAPL", "limit": 5},
     "fundamentals: debt ratios half (D017)"),
    ("cash flow statement", "/stable/cash-flow-statement", {"symbol": "AAPL", "limit": 5},
     "fundamentals: FCF yield half (D017)"),
    ("balance sheet", "/stable/balance-sheet-statement", {"symbol": "AAPL", "limit": 1},
     "T023b debt ratios — the one statements endpoint the 2026-08-17 probe "
     "missed; briefing degrades with a note until this row reads OK"),
    ("earnings calendar (past)", "/stable/earnings-calendar",
     {"from": "2025-01-01", "to": "2025-03-31"},
     "T083 base rates need HISTORICAL earnings dates (+ epsActual for "
     "beat/miss); the 08-17 probe only asked for a future window"),
    ("analyst estimates", "/stable/analyst-estimates",
     {"symbol": "AAPL", "period": "annual", "page": 0, "limit": 1},
     "consensus estimates — commonly paid-tier"),
    ("stock news", "/stable/news/stock", {"symbols": "AAPL"},
     "news as CONTEXT (D019) — competes with Alpaca news we already have"),
    ("transcripts", "/stable/earning-call-transcript",
     {"symbol": "AAPL", "year": 2026, "quarter": 1},
     "owner reports NOT included — this line should confirm it mechanically"),
]


def read_key() -> str | None:
    """FMP_API_KEY from the environment or .env — value never printed."""
    import os

    key = os.environ.get("FMP_API_KEY")
    if key:
        return key
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("FMP_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def classify(status: int, body: str) -> str:
    low = body.lower()
    if status == 200:
        return "OK"
    if status == 429:
        return "RATE LIMITED (free tier is 250 req/day — rerun tomorrow)"
    if status in (401,):
        return "KEY REJECTED (check FMP_API_KEY in .env)"
    if status in (402, 403) or "premium" in low or "upgrade" in low or "subscription" in low:
        return "PAYWALLED on this tier"
    if status == 404:
        return "NOT FOUND (endpoint moved — tell an agent, do not guess)"
    return f"HTTP {status}"


def main() -> int:
    key = read_key()
    if not key:
        print("FMP_API_KEY not found in the environment or .env.")
        print("Your key is at https://site.financialmodelingprep.com/developer/docs")
        return 2

    print("Probing your FMP tier (statuses only, ~3 seconds, 8 of your 250 daily calls)\n")
    print(f"{'endpoint':<24} {'verdict':<44} rows")
    print("-" * 78)
    results = []
    with httpx.Client(base_url="https://financialmodelingprep.com",
                      timeout=30.0) as client:
        for name, path, params, why in PROBES:
            try:
                r = client.get(path, params={**params, "apikey": key})
                # Never echo the key, even if the server reflects the URL back.
                body = re.sub(re.escape(key), "***", r.text[:200])
                verdict = classify(r.status_code, body)
                rows = ""
                if r.status_code == 200:
                    try:
                        data = r.json()
                        rows = str(len(data)) if isinstance(data, list) else "obj"
                        if isinstance(data, list) and not data:
                            verdict = "OK but EMPTY (may be silently tier-limited)"
                    except ValueError:
                        rows = "?"
                print(f"{name:<24} {verdict:<44} {rows}")
                results.append((name, verdict, why))
            except httpx.HTTPError as e:
                print(f"{name:<24} UNREACHABLE ({type(e).__name__})")
                results.append((name, "UNREACHABLE", why))
            time.sleep(0.35)

    print("\nWhat each line decides:")
    for name, verdict, why in results:
        print(f"  - {name}: {why}")
    print("\nPaste the table above into any KUBERA agent session — the T023")
    print("source decision (FMP vs Alpaca news vs skip) reads directly from it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
