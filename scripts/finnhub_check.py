"""T121 — probe Finnhub's FREE tier before building anything on it. Run:

    python scripts\\finnhub_check.py

WHY (D030/D034, lead from the FinRobot review 2026-08-20): Finnhub is an
OFFICIAL API whose free tier plausibly answers company news, basic
sentiment, and earnings-surprise history — surfaces Alpaca's news feed
does not cover. No code gets built against an unobserved tier (T102):
this probe measures, from the machine that will run it, exactly which
endpoints the owner's free key answers.

Get a free key at https://finnhub.io (60 calls/min on the free tier per
their docs — the probe makes 5 calls with polite sleeps). Put it in .env:

    FINNHUB_API_KEY=...

Prints STATUSES and COUNTS only — never the key, never article bodies.
Paste the table to any agent; a FinnhubClient ticket exists only if this
table says the endpoints answer (the FMP/EDGAR precedent).

The sandbox cannot reach finnhub.io — this runs where KUBERA lives.
"""

import os
import sys
import time
from pathlib import Path

import httpx

ROOT_ENV = Path(__file__).resolve().parents[1] / ".env"
BASE = "https://finnhub.io/api/v1"


def load_key() -> str | None:
    key = os.environ.get("FINNHUB_API_KEY", "").strip()
    if not key and ROOT_ENV.exists():
        for raw in ROOT_ENV.read_text(encoding="utf-8",
                                      errors="replace").splitlines():
            if raw.strip().startswith("FINNHUB_API_KEY="):
                key = raw.split("=", 1)[1].strip().strip('"').strip("'")
                break
    return key or None


def line(label: str, verdict: str, extra: str = "") -> None:
    print(f"{label:<30} {verdict:<12} {extra}")


# The endpoints worth measuring, with WHY each matters to KUBERA:
#   company-news        -> would enrich get_news beyond Alpaca's feed
#   news-sentiment      -> labeled qualitative context candidate (D017-safe
#                          only as measurement, never a signal)
#   stock/earnings      -> earnings SURPRISE history (actual vs estimate) —
#                          would enrich T083 base rates with beat/miss
#                          splits KUBERA currently marks "unknown"
#   quote               -> sanity check the key works at all
#   stock/metric        -> basic fundamentals overlap check vs FMP
PROBES = [
    ("quote", "/quote", {"symbol": "AAPL"},
     lambda d: f"c={d.get('c')} (current price present)"
     if isinstance(d, dict) and d.get("c") else None),
    ("company-news", "/company-news",
     {"symbol": "AAPL", "from": "2026-07-20", "to": "2026-08-20"},
     lambda d: f"{len(d)} articles in 31 days"
     if isinstance(d, list) and d else None),
    ("news-sentiment", "/news-sentiment", {"symbol": "AAPL"},
     lambda d: "sentiment object present"
     if isinstance(d, dict) and d.get("symbol") else None),
    ("earnings surprises", "/stock/earnings", {"symbol": "AAPL"},
     lambda d: f"{len(d)} quarters with actual-vs-estimate"
     if isinstance(d, list) and d else None),
    ("stock/metric (basic)", "/stock/metric",
     {"symbol": "AAPL", "metric": "all"},
     lambda d: f"{len((d or {}).get('metric') or {})} metrics"
     if isinstance(d, dict) and (d.get("metric") or {}) else None),
]


def main() -> int:
    key = load_key()
    if not key:
        print("FINNHUB_API_KEY is not set. Free key: https://finnhub.io")
        print("Add one line to .env:  FINNHUB_API_KEY=...   (never committed)")
        return 2
    print("Probing Finnhub free tier (5 requests, polite pacing, key never "
          "echoed)")
    print("-" * 78)
    client = httpx.Client(base_url=BASE, timeout=30.0,
                          params={"token": key})
    try:
        for label, path, params, describe in PROBES:
            try:
                r = client.get(path, params=params)
            except httpx.HTTPError as e:
                line(label, "UNREACHABLE", type(e).__name__)
                continue
            if r.status_code == 401:
                line(label, "BAD KEY", "HTTP 401 — check FINNHUB_API_KEY")
            elif r.status_code == 403:
                line(label, "PAYWALLED", "HTTP 403 — not on the free tier")
            elif r.status_code == 429:
                line(label, "RATE LIMITED", "HTTP 429 — rerun in a minute")
            elif r.status_code != 200:
                line(label, f"HTTP {r.status_code}")
            else:
                try:
                    desc = describe(r.json())
                except ValueError:
                    desc = None
                if desc:
                    line(label, "OK", desc)
                else:
                    line(label, "EMPTY/SHAPE?",
                         "200 but no usable payload — free tier may stub "
                         "this endpoint")
            time.sleep(1.1)  # polite; free tier allows 60/min
    finally:
        client.close()
    print("-" * 78)
    print("What each line decides:")
    print("  - company-news OK      -> a news-enrichment ticket becomes real")
    print("  - earnings surprises OK-> T083 base rates gain beat/miss splits")
    print("    (today 'unknown' dominates; actual-vs-estimate would fix it)")
    print("  - news-sentiment OK    -> labeled context candidate ONLY —")
    print("    measurement, never a signal (D017)")
    print("Paste this table into any KUBERA agent session (D030: probe,")
    print("not brochure). No client gets built unless the table says yes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
