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

_FEES = re.compile(r"Commission\s+(?P<commission>[\d.]+)|Industry Fee\s+(?P<fee>[\d.]+)")


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

    def summary(self) -> str:
        opts = sum(1 for f in self.fills if f.asset_type == "option")
        return (f"{self.files_read} files, {len(self.fills)} fills "
                f"({opts} option / {len(self.fills) - opts} equity), "
                f"{len(self.unparsed)} unparsed")


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


def parse_confirmation(text: str, source_file: str = "") -> ParseReport:
    """Extract every fill from one confirmation's text layer."""
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
        asset_type = "option" if opt else "equity"

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
    out.fills.sort(key=lambda f: (f.trade_date, f.symbol))
    return out


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
            import pypdf
            reader = pypdf.PdfReader(str(p))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
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
    return merge(reports) if reports else ParseReport(files_read=0)
