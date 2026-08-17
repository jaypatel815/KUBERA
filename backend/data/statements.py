"""T102 — parse Schwab trade confirmations (D026).

Built against the owner's REAL confirmations (86 of them, Jan–Jun 2026), not a
guessed layout. Three things the documents actually do, each of which would
silently corrupt the behavioural analysis if handled naively:

1. THE DATE ON THE ROW IS THE SETTLE DATE, NOT THE TRADE DATE.
   A trade executed 03/02 shows "03/03" on its row; the trade date appears only
   in the page header ("March 2, 2026"). Using the row date would shift every
   fill forward by one to two days — quietly wrong in exactly the way that
   ruins holding periods, day-of-week analysis and post-loss timing. So the
   header date is the source of truth and a row without one is REJECTED rather
   than defaulted.

2. ONE CONFIRMATION CAN HOLD SEVERAL FILLS. Same-day round trips arrive as a
   Purchase row and a Sale row on one document. A parser that returns "the"
   trade per file loses half of them.

3. MOST OF THESE ARE OPTIONS — 60 of 86. Option rows carry the expiry, strike
   and right split across continuation lines, and quantity is in CONTRACTS, so
   economic exposure is 100x the number shown. Treating an option row as an
   equity row understates size by two orders of magnitude.

Anything this parser cannot interpret is REPORTED, never dropped — same rule as
the API mapper (data/schwab.py), for the same reason: reconciliation against a
statement only works if the importer admits what it skipped.

PRIVACY: the source PDFs live in `private/` (gitignored — the repo is public,
and a confirmation carries the account number and address). This module extracts
trades only; it never returns or logs the name, address or account number, and
`redact()` exists to build committable test fixtures.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

OPTION_MULTIPLIER = 100

# "March 2, 2026" in the page header — the real trade date.
_HEADER_DATE = re.compile(
    r"\b(January|February|March|April|May|June|July|August|September|October|"
    r"November|December)\s+(\d{1,2}),\s+(20\d\d)\b"
)

# "03/03 Purchase XLE   DESCRIPTION ...   25   56.59"
# Settle date is optional because a second row on the same document omits it.
_ROW = re.compile(
    r"^\s*(?P<settle>\d{2}/\d{2})?\s*"
    r"(?P<action>Purchase|Sale|Bought|Sold)\s+"
    r"(?P<symbol>[A-Z][A-Z0-9./]{0,10})\s+"
    r"(?P<rest>.+?)\s{2,}"
    r"(?P<qty>[\d,]+(?:\.\d+)?)\s+"
    r"(?P<price>[\d,]+\.\d+)"
)

# "State Street SPDR S&P 500 ETF Trust 03/30/2026 $630 Put"
_OPTION = re.compile(
    r"(?P<expiry>\d{2}/\d{2}/\d{4})\s+"
    r"\$?(?P<strike>[\d,]+(?:\.\d+)?)\s+"
    r"(?P<right>Put|Call)"
)

# Fallback option identity: the broker's own "656.00 C" column on a
# continuation line, plus a full MM/DD/YYYY expiry anywhere in the row window.
# Needed because long descriptions WRAP — "…Trust 03/24/2026 $656" ends one
# line and "Call" starts another with the expiry column interleaved, so the
# contiguous pattern above cannot see it. Found on a real confirmation whose
# SPY 656C buy was silently misread as 3 SHARES of SPY at $0.45 (T108).
_OPTION_IDENTITY = re.compile(r"\b(?P<strike>\d{1,6}(?:,\d{3})*\.\d{2})\s+(?P<letter>[PC])\b")
_OPTION_HINT = re.compile(r"\b(Put|Call)\b|\$[\d,]+(?:\.\d+)?\s*(?:Put|Call)")
_FULL_DATE = re.compile(r"\b(\d{2}/\d{2}/\d{4})\b")

_FEES = re.compile(r"Commission\s+(?P<commission>[\d.]+)|Industry Fee\s+(?P<fee>[\d.]+)")

# Monthly account statements are NOT trade confirmations, but in layout-mode
# extraction their Transaction Details rows match _ROW well enough to parse —
# and every trade in them ALSO has its own confirmation, so parsing both
# double-counts every fill. "Statement Period" appears in the header of all 5
# of the owner's monthly statements and none of his 86 confirmations (checked
# against the real documents, 2026-08-17). Detection is content-based first,
# filename second, because files get renamed.
_STATEMENT_PERIOD = re.compile(r"Statement\s+Period", re.IGNORECASE)


@dataclass(frozen=True)
class ParsedFill:
    """One executed fill. Field names mirror data.alpaca.Fill so the analysis
    layer consumes these unchanged."""

    trade_date: date
    settle_date: date | None
    symbol: str
    side: str                      # buy | sell
    qty: float                     # CONTRACTS for options, shares for equity
    price: float
    description: str
    asset_type: str                # equity | option
    commission: float = 0.0
    fees: float = 0.0
    option_expiry: date | None = None
    option_strike: float | None = None
    option_right: str | None = None   # put | call
    source_file: str = ""

    @property
    def notional(self) -> float:
        """Economic exposure. Options are per-contract — 100 shares each — and
        forgetting that understates position size by 100x."""
        mult = OPTION_MULTIPLIER if self.asset_type == "option" else 1
        return round(self.qty * self.price * mult, 2)


@dataclass(frozen=True)
class ParseReport:
    fills: list[ParsedFill] = field(default_factory=list)
    unparsed: list[dict] = field(default_factory=list)
    files_read: int = 0
    # Files dropped because they are re-downloads of a daily confirmation
    # already kept (T108). Reported, never silent — same rule as unparsed.
    duplicates: list[dict] = field(default_factory=list)

    def summary(self) -> str:
        opts = sum(1 for f in self.fills if f.asset_type == "option")
        dup = f", {len(self.duplicates)} duplicate files dropped" if self.duplicates else ""
        return (f"{self.files_read} files, {len(self.fills)} fills "
                f"({opts} option / {len(self.fills) - opts} equity), "
                f"{len(self.unparsed)} unparsed{dup}")


def header_trade_date(text: str) -> date | None:
    """The trade date, from the page header. None if absent — never guessed."""
    m = _HEADER_DATE.search(text)
    if not m:
        return None
    try:
        return datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", "%B %d %Y").date()
    except ValueError:
        return None


def _settle(token: str | None, trade: date) -> date | None:
    """MM/DD with no year — resolve against the trade date, rolling the year at
    a December/January boundary rather than producing a date 11 months early."""
    if not token:
        return None
    try:
        month, day = (int(x) for x in token.split("/"))
    except ValueError:
        return None
    year = trade.year + 1 if (trade.month == 12 and month == 1) else trade.year
    try:
        return date(year, month, day)
    except ValueError:
        return None


def is_monthly_statement(text: str, source_file: str = "") -> bool:
    """True if this is a monthly account statement rather than a confirmation."""
    if Path(source_file).name.lower().startswith("brokerage statement"):
        return True
    return bool(_STATEMENT_PERIOD.search(text))


def parse_confirmation(text: str, source_file: str = "") -> ParseReport:
    """Extract every fill from one confirmation's text layer."""
    if is_monthly_statement(text, source_file):
        return ParseReport(
            files_read=1,
            unparsed=[{"file": source_file,
                       "why": "monthly account statement, not a trade confirmation — "
                              "every trade here also has its own confirmation, so parsing "
                              "both would double-count. Used by expiry reconciliation "
                              "(T108) instead."}],
        )
    trade = header_trade_date(text)
    if trade is None:
        return ParseReport(
            files_read=1,
            unparsed=[{"file": source_file, "why": "no trade date in the header — "
                                                   "refusing to fall back to the settle date"}],
        )

    lines = text.splitlines()
    fills: list[ParsedFill] = []
    unparsed: list[dict] = []

    # Find every row FIRST, so each row's continuation window can be bounded by
    # the next row. A fixed lookahead is wrong here and not subtly so: these are
    # DAILY confirmations carrying every trade for the day, so a 4-line window
    # reached into the next trade and tagged an equity ETF purchase as a 180 put.
    # The bug was invisible in aggregate (0 unparsed, plausible totals) and only
    # showed up when the per-file fills were read one by one.
    starts = [i for i, line in enumerate(lines) if _ROW.match(line)]

    for n, i in enumerate(starts):
        line = lines[i]
        m = _ROW.match(line)
        if m is None:                     # unreachable; keeps the checker honest
            continue

        rest = m.group("rest").strip()
        end = starts[n + 1] if n + 1 < len(starts) else len(lines)
        window = " ".join(x.strip() for x in lines[i:end])

        opt = _OPTION.search(rest) or _OPTION.search(window)
        # Wrapped-description fallback: no contiguous "expiry $strike Right",
        # but the identity column ("656.00 C") plus a full date is present.
        fallback = None
        if not opt:
            idm = _OPTION_IDENTITY.search(window)
            dm = _FULL_DATE.search(window)
            if idm and dm:
                fallback = (dm.group(1), idm.group("strike"), idm.group("letter"))
            elif idm or _OPTION_HINT.search(window):
                # Option evidence exists but cannot be fully assembled. Calling
                # this row EQUITY would book contracts as shares at premium
                # prices — silently and 100x wrong. Report it instead.
                unparsed.append({"file": source_file, "line": line.strip()[:80],
                                 "why": "option evidence in the row window but no "
                                        "complete expiry/strike/right — refusing to "
                                        "classify as equity"})
                continue
        asset_type = "option" if (opt or fallback) else "equity"

        commission = fees = 0.0
        for fm in _FEES.finditer(window):
            if fm.group("commission"):
                commission += float(fm.group("commission"))
            if fm.group("fee"):
                fees += float(fm.group("fee"))

        try:
            qty = float(m.group("qty").replace(",", ""))
            price = float(m.group("price").replace(",", ""))
        except ValueError:
            unparsed.append({"file": source_file, "line": line.strip()[:80],
                             "why": "quantity or price not numeric"})
            continue

        expiry = strike = right = None
        if opt:
            try:
                expiry = datetime.strptime(opt.group("expiry"), "%m/%d/%Y").date()
                strike = float(opt.group("strike").replace(",", ""))
                right = opt.group("right").lower()
            except ValueError:
                unparsed.append({"file": source_file, "line": rest[:80],
                                 "why": "option leg present but unparseable"})
                continue
        elif fallback:
            try:
                expiry = datetime.strptime(fallback[0], "%m/%d/%Y").date()
                strike = float(fallback[1].replace(",", ""))
                right = "put" if fallback[2] == "P" else "call"
            except ValueError:
                unparsed.append({"file": source_file, "line": rest[:80],
                                 "why": "wrapped option leg present but unparseable"})
                continue

        fills.append(ParsedFill(
            trade_date=trade,
            settle_date=_settle(m.group("settle"), trade),
            symbol=m.group("symbol").upper(),
            side="buy" if m.group("action").lower() in {"purchase", "bought"} else "sell",
            qty=qty,
            price=price,
            description=re.sub(r"\s{2,}", " ", rest)[:120],
            asset_type=asset_type,
            commission=round(commission, 4),
            fees=round(fees, 4),
            option_expiry=expiry,
            option_strike=strike,
            option_right=right,
            source_file=source_file,
        ))

    if not fills and not unparsed:
        unparsed.append({"file": source_file, "why": "no fill rows matched"})
    return ParseReport(fills=fills, unparsed=unparsed, files_read=1)


def merge(reports: list[ParseReport]) -> ParseReport:
    out = ParseReport(files_read=sum(r.files_read for r in reports))
    for r in reports:
        out.fills.extend(r.fills)
        out.unparsed.extend(r.unparsed)
        out.duplicates.extend(r.duplicates)
    out.fills.sort(key=lambda f: (f.trade_date, f.symbol))
    return out


def _fill_signature(f: ParsedFill) -> tuple:
    """Identity of one fill for duplicate-document detection. Excludes
    source_file (that is exactly what differs between copies) and description
    (extraction noise varies between downloads of the same document)."""
    return (f.trade_date, f.symbol, f.side, f.qty, f.price, f.asset_type,
            f.option_expiry, f.option_strike, f.option_right)


def dedupe_daily_documents(reports: list[ParseReport]) -> list[ParseReport]:
    """Drop re-downloads of the same daily confirmation (T108).

    Schwab's confirmation for day D lists EVERY trade of day D, and saving it
    once per trade — "Confirm - AAPL …", "Confirm - NVDA …", same document,
    different names — multi-counts the whole day. On the owner's real folder
    this inflated 24 separate days (the same three NVDA fills counted three
    times, phantom open lots, a 9-vs-3 contract mismatch against the monthly
    statement).

    Files whose bytes differ but whose FILL-SETS are identical for the same
    trade date are copies: keep the first, report the rest. A strict subset
    (an intraday download superseded by the end-of-day one) is dropped in
    favour of the superset. Sets that overlap WITHOUT nesting are kept AND
    loudly reported — that shape would mean real double-counting this code
    cannot resolve, and guessing is not an option.
    """
    from collections import defaultdict

    by_date: dict = defaultdict(list)   # trade_date -> [(report, multiset)]
    passthrough: list[ParseReport] = []
    for r in reports:
        dates = {f.trade_date for f in r.fills}
        if len(dates) != 1:
            passthrough.append(r)       # no fills, or multi-date: nothing to collapse
            continue
        sig = sorted(_fill_signature(f) for f in r.fills)
        by_date[dates.pop()].append((r, sig))

    kept: list[ParseReport] = list(passthrough)
    for _day, group in sorted(by_date.items()):
        # Largest first so subsets meet their superset.
        group.sort(key=lambda pair: (-len(pair[1]), (pair[0].fills[0].source_file or "")))
        chosen: list[tuple[ParseReport, list]] = []
        for r, sig in group:
            verdict = None
            for kept_r, kept_sig in chosen:
                if sig == kept_sig:
                    verdict = ("duplicate download of the same daily confirmation as "
                               f"'{kept_r.fills[0].source_file}' — identical fills, dropped")
                    break
                kset, sset = set(map(tuple, kept_sig)), set(map(tuple, sig))
                if sset < kset:
                    verdict = ("partial duplicate (subset) of "
                               f"'{kept_r.fills[0].source_file}' — dropped")
                    break
                if sset & kset:
                    # Overlap without nesting: keep, but say so loudly.
                    r = ParseReport(
                        fills=r.fills, files_read=r.files_read,
                        unparsed=r.unparsed + [{
                            "file": r.fills[0].source_file,
                            "why": "OVERLAPPING fill-sets with "
                                   f"'{kept_r.fills[0].source_file}' on the same day — "
                                   "possible double-count, resolve manually",
                        }],
                        duplicates=r.duplicates,
                    )
                    break
            if verdict:
                kept.append(ParseReport(
                    files_read=r.files_read,
                    duplicates=[{"file": r.fills[0].source_file, "why": verdict}],
                ))
            else:
                chosen.append((r, sig))
                kept.append(r)
    return kept


def redact(text: str) -> str:
    """Strip identity from a confirmation so it can become a committed fixture.

    Removes the account number, the name/address block and the ZIP. Deliberately
    conservative: it is better to over-redact a fixture than to publish one line
    of a real address to a public repository.
    """
    out = re.sub(r"\b\d{4}-\d{4}\b", "0000-0000", text)          # account number
    out = re.sub(r"\b\d{5}-\d{4}\b", "00000-0000", out)          # ZIP+4
    out = re.sub(r"\b\d{6,}\b", "000000", out)                   # any long digit run
    # Address-shaped lines: a street number followed by words.
    out = re.sub(r"(?m)^\s*\d+\s+[A-Z][A-Z0-9 .#]{4,}$", "  [REDACTED ADDRESS]", out)
    out = re.sub(r"Schwab One® Account of.*", "Schwab One® Account of [REDACTED]", out)
    return out


def extract_pdf_text(path: str | Path) -> str:
    """Text layer of a PDF, preferring pypdf's layout extraction mode.

    NOT a cosmetic choice: the row regexes here depend on 2+ spaces between
    columns, and the DEFAULT ("plain") mode's line-joining changes between
    pypdf versions — 6.13 splits what 5.x kept on one line, which silently
    turned all 86 of the owner's real confirmations into "no fill rows
    matched" (I027). Layout mode preserves the columns on every version that
    has it; the TypeError branch keeps pypdf < 3.17 working on plain mode,
    which is the joining this parser was originally built against.
    """
    import pypdf

    reader = pypdf.PdfReader(str(path))
    pages: list[str] = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text(extraction_mode="layout") or "")
        except TypeError:  # pypdf < 3.17 has no extraction_mode parameter
            pages.append(page.extract_text() or "")
    return "\n".join(pages)


def parse_file(path: str | Path) -> ParseReport:
    """Parse a single trade confirmation file (.txt or .pdf)."""
    p = Path(path)
    if not p.exists():
        return ParseReport(
            unparsed=[{"file": str(p), "why": "file does not exist"}],
            files_read=0,
        )

    if p.suffix.lower() in {".txt", ".text"}:
        text = p.read_text(encoding="utf-8", errors="replace")
        return parse_confirmation(text, source_file=p.name)

    if p.suffix.lower() == ".pdf":
        try:
            text = extract_pdf_text(p)
            return parse_confirmation(text, source_file=p.name)
        except ImportError:
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
                return parse_confirmation(text, source_file=p.name)
            except Exception as e:
                return ParseReport(
                    unparsed=[{"file": p.name, "why": f"PDF extraction failed ({e})"}],
                    files_read=1,
                )
        except Exception as e:
            return ParseReport(
                unparsed=[{"file": p.name, "why": f"PDF parse error ({e})"}],
                files_read=1,
            )

    try:
        text = p.read_text(encoding="utf-8", errors="replace")
        return parse_confirmation(text, source_file=p.name)
    except Exception as e:
        return ParseReport(
            unparsed=[{"file": p.name, "why": f"read error ({e})"}],
            files_read=1,
        )


def parse_directory(dir_path: str | Path) -> ParseReport:
    """Parse all trade confirmations (.txt and .pdf) in a directory."""
    p = Path(dir_path)
    if not p.exists() or not p.is_dir():
        return ParseReport(files_read=0)

    reports = []
    for item in sorted(p.iterdir()):
        if item.is_file() and item.suffix.lower() in {".txt", ".pdf"}:
            reports.append(parse_file(item))
    if not reports:
        return ParseReport(files_read=0)
    return merge(dedupe_daily_documents(reports))
