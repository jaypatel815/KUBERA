"""T083b — SEC EDGAR earnings-8-K history (D030/D034). Free, keyless, probed.

What the owner's probe measured (2026-08-18, his machine): company_tickers.json
OK (10,387 tickers); submissions JSON OK (1,000 recent filings for the probe
symbol, columnar arrays); 105 8-Ks of which 46 carry item "2.02" (results of
operations — the earnings 8-K); 46/46 with acceptanceDateTime; recent-window
history back to 2015. This client speaks EXACTLY that shape and nothing else.

Why this exists: the owner's FMP tier answers only the FORWARD earnings
calendar (past windows paywalled, D034). EDGAR supplies YEARS of past
earnings dates immediately — and its acceptanceDateTime is a REAL clock,
which beats bmo/amc hints: T083's reaction-day convention upgrades from
assumed to KNOWN for EDGAR-sourced dates.

Etiquette (SEC's own rules): a User-Agent with a contact address — loaded
from settings (EDGAR_CONTACT), never logged, never committed; no retry
loops; the ticker map is fetched once per client and cached. Fail-closed
parsing per T102: a filing row missing its date is REPORTED in `unparsed`,
never guessed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone

import httpx

from settings import ConfigError, KuberaSettings, get_settings

EARNINGS_ITEM = "2.02"          # Results of Operations and Financial Condition


class EdgarError(RuntimeError):
    pass


@dataclass(frozen=True)
class EarningsFiling:
    symbol: str
    filing_date: date
    acceptance_utc: datetime | None   # real clock; None only if EDGAR omits it
    items: str


@dataclass(frozen=True)
class EdgarEarningsHistory:
    symbol: str
    cik: int
    filings: list[EarningsFiling] = field(default_factory=list)
    unparsed: list[dict] = field(default_factory=list)
    asof: str = ""
    source: str = "sec-edgar"


def _parse_acceptance(raw: object) -> datetime | None:
    """'2026-07-30T20:30:28.000Z' -> aware UTC datetime; None if absent/bad
    (the caller records the row as date-only — timing then falls back to the
    assumed convention, counted, exactly like a missing bmo/amc hint)."""
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


class EdgarClient:
    """Read-only, two endpoints only, transport-injectable for tests."""

    def __init__(self, settings: KuberaSettings | None = None,
                 transport: httpx.BaseTransport | None = None):
        s = settings or get_settings()
        if not s.edgar_contact or not s.edgar_contact.get_secret_value().strip():
            raise ConfigError(
                "EDGAR_CONTACT is not set. The SEC requires a contact address "
                "in the User-Agent of automated clients (they block anonymous "
                "ones). Add EDGAR_CONTACT=you@example.com to .env — it stays "
                "on your machine."
            )
        ua = f"KUBERA personal-research {s.edgar_contact.get_secret_value().strip()}"
        headers = {"User-Agent": ua, "Accept-Encoding": "gzip, deflate"}
        self._data = httpx.Client(base_url=s.edgar_base_url, headers=headers,
                                  timeout=30.0, transport=transport,
                                  follow_redirects=True)
        self._www = httpx.Client(base_url=s.edgar_www_url, headers=headers,
                                 timeout=30.0, transport=transport,
                                 follow_redirects=True)
        self._cik_by_ticker: dict[str, int] | None = None

    def close(self) -> None:
        self._data.close()
        self._www.close()

    def __enter__(self) -> "EdgarClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _get_json(self, client: httpx.Client, path: str, what: str):
        r = client.get(path)
        if r.status_code == 403:
            raise EdgarError(
                f"EDGAR refused {what} (HTTP 403) — usually the User-Agent. "
                "Confirm EDGAR_CONTACT is a real contact address.")
        if r.status_code == 429:
            raise EdgarError(
                "EDGAR rate limit (HTTP 429) — the ceiling is ~10 req/s; "
                "do not retry in a loop.")
        if r.status_code >= 400:
            raise EdgarError(f"EDGAR {what} failed: HTTP {r.status_code}")
        try:
            return r.json()
        except ValueError as e:
            raise EdgarError(f"EDGAR {what} returned non-JSON") from e

    def cik_for(self, symbol: str) -> int:
        """Resolve ticker -> CIK from company_tickers.json (fetched once)."""
        if self._cik_by_ticker is None:
            data = self._get_json(self._www, "/files/company_tickers.json",
                                  "company_tickers.json")
            if not isinstance(data, dict):
                raise EdgarError("company_tickers.json is not an object — "
                                 "shape changed; refusing to guess")
            mapping: dict[str, int] = {}
            for row in data.values():
                if isinstance(row, dict) and row.get("ticker") and \
                        row.get("cik_str") is not None:
                    try:
                        mapping[str(row["ticker"]).upper()] = int(row["cik_str"])
                    except (TypeError, ValueError):
                        continue
            if not mapping:
                raise EdgarError("company_tickers.json parsed to an empty map")
            self._cik_by_ticker = mapping
        cik = self._cik_by_ticker.get(symbol.upper())
        if cik is None:
            raise EdgarError(
                f"'{symbol.upper()}' is not in EDGAR's ticker map — check the "
                "symbol (ETFs and some foreign listings have no CIK)")
        return cik

    def earnings_history(self, symbol: str) -> EdgarEarningsHistory:
        """All item-2.02 8-Ks in the recent submissions window, oldest first.

        The probe measured ~11 years for a large filer in the recent window
        alone; paged archive files exist for older history and are NOT
        fetched (unobserved shape — a future ticket if ever needed).
        """
        symbol = symbol.upper()
        cik = self.cik_for(symbol)
        sub = self._get_json(self._data, f"/submissions/CIK{cik:0>10}.json",
                             "submissions JSON")
        recent = (sub.get("filings") or {}).get("recent") or {}
        forms = recent.get("form") or []
        dates = recent.get("filingDate") or []
        items = recent.get("items") or []
        accept = recent.get("acceptanceDateTime") or []
        if not forms or not dates:
            raise EdgarError("submissions JSON carries no recent filings — "
                             "shape changed; refusing to guess")

        filings: list[EarningsFiling] = []
        unparsed: list[dict] = []
        for i, form in enumerate(forms):
            if form != "8-K":
                continue
            row_items = str(items[i]) if i < len(items) else ""
            if EARNINGS_ITEM not in row_items:
                continue
            raw_date = dates[i] if i < len(dates) else None
            try:
                fdate = date.fromisoformat(str(raw_date))
            except (TypeError, ValueError):
                unparsed.append({"why": "8-K item 2.02 with unparseable "
                                        "filingDate — refusing to guess",
                                 "row": str(raw_date)[:20]})
                continue
            filings.append(EarningsFiling(
                symbol=symbol,
                filing_date=fdate,
                acceptance_utc=_parse_acceptance(
                    accept[i] if i < len(accept) else None),
                items=row_items,
            ))
        filings.sort(key=lambda f: f.filing_date)
        return EdgarEarningsHistory(
            symbol=symbol, cik=cik, filings=filings, unparsed=unparsed,
            asof=datetime.now(timezone.utc).isoformat(),
        )
