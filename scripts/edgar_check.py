"""T083b — probe SEC EDGAR before building anything on it. Run on your machine:

    python scripts\\edgar_check.py

WHY THIS EXISTS (D030/D034): the owner's FMP tier answers only the FORWARD
earnings calendar (past windows paywalled, measured 2026-08-18), so T083's
base rates accumulate quarter by quarter. EDGAR 8-K filings (item 2.02 =
results of operations) are free, keyless, and authoritative — they could
supply YEARS of past earnings dates immediately. But no code gets built
against an unobserved API (T102), so this probe measures, from the machine
that will run it:

  1. the ticker->CIK mapping file (company_tickers.json): reachable? shape?
  2. one company's submissions JSON: 8-K count, whether the `items` field
     really carries "2.02", how far back `filingDate` reaches
  3. acceptanceDateTime presence — EDGAR's clock is BETTER than bmo/amc
     hints (a real timestamp: before 09:30 ET = pre-open, after 16:00 = post-
     close), which upgrades T083's timing convention from assumed to known
  4. the etiquette EDGAR requires: a declared User-Agent with contact info
     (SEC blocks anonymous UAs), ~10 requests/second documented ceiling

Prints STATUSES, COUNTS, and THREE sample rows (dates+times only — filings
are public documents, but the probe stays terse by policy). Paste the table
to any agent; the T083b build decision reads from it.

The sandbox cannot reach sec.gov — this runs where KUBERA will live.
"""

import os
import sys
import time
from pathlib import Path

import httpx

ROOT_ENV = Path(__file__).resolve().parents[1] / ".env"

# SEC etiquette: identify yourself — they BLOCK generic/empty user agents and
# ask for a contact address in the UA. The contact comes from .env
# (EDGAR_CONTACT), NOT from this file: the repo is PUBLIC, and an email in
# committed source is harvestable PII — the same discipline as the masked
# account numbers and redacted statements.


def build_user_agent() -> str | None:
    contact = os.environ.get("EDGAR_CONTACT", "").strip()
    if not contact:
        # Try .env the cheap way (no dependency on backend settings).
        env_file = ROOT_ENV
        if env_file.exists():
            for raw in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
                if raw.strip().startswith("EDGAR_CONTACT="):
                    contact = raw.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    return f"KUBERA personal-research {contact}" if contact else None


TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:0>10}.json"
PROBE_TICKER = "AAPL"          # any large filer works; AAPL files everything


def line(label: str, verdict: str, extra: str = "") -> None:
    print(f"{label:<28} {verdict:<12} {extra}")


def main() -> int:
    ua = build_user_agent()
    if ua is None:
        print("EDGAR_CONTACT is not set. SEC requires a contact address in the")
        print("User-Agent (they block anonymous clients). Add one line to .env:")
        print("    EDGAR_CONTACT=you@example.com")
        print("It stays on your machine — never committed (the repo is public).")
        return 2
    print("Probing SEC EDGAR (keyless, ~3 requests, declared User-Agent)")
    print("UA: KUBERA personal-research <contact from .env — not echoed>")
    print("-" * 78)
    headers = {"User-Agent": ua, "Accept-Encoding": "gzip, deflate"}
    client = httpx.Client(headers=headers, timeout=30.0, follow_redirects=True)

    # 1. ticker -> CIK mapping
    cik = None
    try:
        r = client.get(TICKER_MAP_URL)
        if r.status_code != 200:
            line("ticker->CIK map", f"HTTP {r.status_code}")
        else:
            data = r.json()
            # Documented shape: {"0": {"cik_str": 320193, "ticker": "AAPL", ...}, ...}
            rows = list(data.values()) if isinstance(data, dict) else []
            hit = next((row for row in rows
                        if str(row.get("ticker", "")).upper() == PROBE_TICKER), None)
            if hit:
                cik = int(hit["cik_str"])
                line("ticker->CIK map", "OK",
                     f"{len(rows)} tickers; {PROBE_TICKER} -> CIK {cik}")
            else:
                line("ticker->CIK map", "SHAPE?",
                     f"{len(rows)} rows but {PROBE_TICKER} not found — "
                     "shape may have changed")
    except httpx.HTTPError as e:
        line("ticker->CIK map", "UNREACHABLE", type(e).__name__)

    time.sleep(0.2)  # well under the ~10/s ceiling; politeness costs nothing

    # 2+3. submissions JSON for the probe company
    if cik is None:
        line("submissions JSON", "SKIPPED", "no CIK from step 1")
        print("-" * 78)
        print("Verdict incomplete — paste whatever printed above to an agent.")
        return 1
    try:
        r = client.get(SUBMISSIONS_URL.format(cik=cik))
        if r.status_code != 200:
            line("submissions JSON", f"HTTP {r.status_code}")
            return 1
        sub = r.json()
        recent = sub.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        items = recent.get("items", [])
        accept = recent.get("acceptanceDateTime", [])
        n = len(forms)
        line("submissions JSON", "OK", f"{n} recent filings for {PROBE_TICKER}")

        eightk_idx = [i for i, f in enumerate(forms) if f == "8-K"]
        line("8-K filings", "OK" if eightk_idx else "NONE",
             f"{len(eightk_idx)} of {n} recent")

        with_202 = [i for i in eightk_idx
                    if i < len(items) and "2.02" in str(items[i])]
        line("items carries 2.02", "OK" if with_202 else "ABSENT",
             f"{len(with_202)} earnings 8-Ks (item 2.02)")

        has_accept = [i for i in with_202 if i < len(accept) and accept[i]]
        line("acceptanceDateTime", "OK" if has_accept else "ABSENT",
             f"{len(has_accept)} of {len(with_202)} carry a timestamp")

        if dates and eightk_idx:
            oldest = min(dates[i] for i in eightk_idx if i < len(dates))
            line("history depth (recent)", "INFO",
                 f"oldest recent-window 8-K: {oldest} "
                 "(older filings live in paged archive files)")

        print()
        print("Sample earnings 8-Ks (date, acceptance time — dates only, no bodies):")
        for i in with_202[:3]:
            d = dates[i] if i < len(dates) else "?"
            a = accept[i] if i < len(accept) else "?"
            print(f"  {d}  accepted {a}")
    except httpx.HTTPError as e:
        line("submissions JSON", "UNREACHABLE", type(e).__name__)
        return 1
    except (ValueError, KeyError) as e:
        line("submissions JSON", "SHAPE?", f"{type(e).__name__}: {e}")
        return 1
    finally:
        client.close()

    print("-" * 78)
    print("What each line decides:")
    print("  - ticker->CIK map: can KUBERA resolve symbols without a key")
    print("  - items carries 2.02: earnings 8-Ks are IDENTIFIABLE (the whole point)")
    print("  - acceptanceDateTime: real clocks beat bmo/amc hints — T083's")
    print("    timing convention upgrades from assumed to KNOWN")
    print("  - history depth: how many past quarters arrive instantly")
    print("Paste this table into any KUBERA agent session — the T083b build")
    print("decision reads directly from it (D030: probe, not brochure).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
