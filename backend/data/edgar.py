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
from html.parser import HTMLParser

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


@dataclass(frozen=True)
class EarningsRelease:
    """T084 — the text of a company's own earnings release (exhibit 99.1),
    free from EDGAR. Labeled qualitative CONTEXT, never a priced signal —
    and honestly NOT the analyst-call Q&A (that stays paid-tier, D034)."""

    symbol: str
    cik: int
    accession: str
    filing_date: date
    acceptance_utc: datetime | None
    doc_name: str
    doc_kind: str                 # "ex99-exhibit" or "8-K primary (no ex99)"
    text: str                     # extracted, whitespace-normalized, capped
    text_chars_total: int         # before the cap — the cap is visible
    truncated: bool
    asof: str = ""
    source: str = "sec-edgar"


def _is_ex99(name: str) -> bool:
    """Exhibit-99 filename rule: collapse to alphanumerics, look for 'ex99'.
    Catches ex991.htm / ex-99_1.htm / d12dex991.htm / a8-kex991q3....htm.
    Same rule the T084a probe used — validated against the owner's observed
    accession (a8-kex991q3202606272026.htm, 173,484 bytes, 2026-08-19)."""
    return "ex99" in "".join(c for c in name.lower() if c.isalnum())


_SKIP_TAGS = frozenset({"script", "style", "head", "title"})
_BLOCK_TAGS = frozenset({"p", "div", "tr", "table", "br", "li", "ul", "ol",
                         "h1", "h2", "h3", "h4", "h5", "h6", "section"})


class _TextExtractor(HTMLParser):
    """Deterministic HTML→text: skip script/style, newline at block edges,
    two spaces between table cells. Financial tables FLATTEN — acceptable
    for qualitative context; the money math never reads this."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        elif tag in _BLOCK_TAGS:
            self.chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
        elif tag in _BLOCK_TAGS:
            self.chunks.append("\n")
        elif tag in ("td", "th"):
            self.chunks.append("  ")

    def handle_data(self, data: str) -> None:
        if not self._skip_depth and data:
            self.chunks.append(data)


def html_to_text(html: str) -> str:
    """Extract readable text; collapse runs of blank lines to one."""
    p = _TextExtractor()
    p.feed(html)
    p.close()
    lines = [" ".join(ln.split()) for ln in "".join(p.chunks).splitlines()]
    out: list[str] = []
    for ln in lines:
        if ln:
            out.append(ln)
        elif out and out[-1] != "":
            out.append("")
    return "\n".join(out).strip()


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

    def _get_text(self, client: httpx.Client, path: str, what: str) -> str:
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
        return r.text

    def earnings_release(self, symbol: str,
                         max_chars: int = 20_000) -> EarningsRelease:
        """T084 — the text of the NEWEST earnings 8-K's press release
        (largest ex99* exhibit; owner-observed 2026-08-19: 173,484 bytes
        free). Named fallback to the 8-K primary document when an accession
        carries no ex99 exhibit. Three requests: submissions (cik map is
        cached), index.json, the document."""
        symbol = symbol.upper()
        cik = self.cik_for(symbol)
        sub = self._get_json(self._data, f"/submissions/CIK{cik:0>10}.json",
                             "submissions JSON")
        recent = (sub.get("filings") or {}).get("recent") or {}
        forms = recent.get("form") or []
        dates = recent.get("filingDate") or []
        items = recent.get("items") or []
        accs = recent.get("accessionNumber") or []
        prims = recent.get("primaryDocument") or []
        accept = recent.get("acceptanceDateTime") or []

        best: tuple[date, int] | None = None
        for i, form in enumerate(forms):
            if form != "8-K":
                continue
            if EARNINGS_ITEM not in (str(items[i]) if i < len(items) else ""):
                continue
            try:
                fdate = date.fromisoformat(str(dates[i] if i < len(dates)
                                               else None))
            except (TypeError, ValueError):
                continue                      # unparsed rows counted elsewhere
            if best is None or fdate > best[0]:
                best = (fdate, i)
        if best is None:
            raise EdgarError(
                f"no earnings 8-K (item {EARNINGS_ITEM}) in the recent window "
                f"for '{symbol}' — ETFs and funds file none")
        fdate, i = best
        acc = str(accs[i]) if i < len(accs) and accs[i] else ""
        if not acc:
            raise EdgarError("earnings 8-K row carries no accessionNumber — "
                             "shape changed; refusing to guess")
        primary = str(prims[i]) if i < len(prims) and prims[i] else ""
        folder = f"/Archives/edgar/data/{cik}/{acc.replace('-', '')}"

        idx = self._get_json(self._www, f"{folder}/index.json", "filing index")
        idx_items = (idx.get("directory") or {}).get("item") \
            if isinstance(idx, dict) else None
        if not isinstance(idx_items, list):
            raise EdgarError("filing index shape changed (directory.item is "
                             "not a list) — refusing to guess")

        def _size(v: object) -> int:
            try:
                return int(str(v).strip() or 0)
            except ValueError:
                return 0

        files = [(str(it["name"]), _size(it.get("size")))
                 for it in idx_items if isinstance(it, dict) and it.get("name")]
        exhibits = [f for f in files if _is_ex99(f[0])]
        if exhibits:
            doc_name = max(exhibits, key=lambda f: f[1])[0]
            doc_kind = "ex99-exhibit"
        elif primary and any(n == primary for n, _ in files):
            doc_name = primary
            doc_kind = "8-K primary (no ex99 exhibit in this accession)"
        else:
            raise EdgarError(
                f"accession {acc} lists no ex99* exhibit and no readable "
                "primary document — nothing safe to read")

        html = self._get_text(self._www, f"{folder}/{doc_name}",
                              f"document {doc_name}")
        text = html_to_text(html)
        if not text:
            raise EdgarError(f"document {doc_name} produced no text — "
                             "refusing to summarize nothing")
        return EarningsRelease(
            symbol=symbol, cik=cik, accession=acc, filing_date=fdate,
            acceptance_utc=_parse_acceptance(
                accept[i] if i < len(accept) else None),
            doc_name=doc_name, doc_kind=doc_kind,
            text=text[:max_chars], text_chars_total=len(text),
            truncated=len(text) > max_chars,
            asof=datetime.now(timezone.utc).isoformat(),
        )
