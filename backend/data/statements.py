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
from datetime import date, datetime, timedelta
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

# Monthly account statements (T108, T108b)
_STATEMENT_PERIOD = re.compile(r"Statement\s+Period", re.IGNORECASE)
_STMT_ACTION = re.compile(r"\b(?P<action>Purchase|Sale)\b")
_STMT_QTY_PRICE = re.compile(r"\(?(?P<val>\d{1,6}(?:,\d{3})*(?:\.\d+)?)\)?")
_STMT_SETTLE_DATE = re.compile(r"^(\d{2})/(\d{2})\s+")
_STMT_END_SECTION = re.compile(
    r"Ending\s+Cash|Total\s+(?:Purchases|Sales|Transactions|Pending)|"
    r"Pending\s*(?:/\s*Open\s*Activity|\s+Transactions)",
    re.IGNORECASE,
)
_STMT_SKIP_LINE = ("Pending", "Beginning Cash")


def is_us_market_holiday(d: date) -> bool:
    """True if d is a scheduled US equity/options market holiday (NYSE / Nasdaq).

    Observed holidays:
    - New Year's Day (Jan 1, observed Mon if Sun, Fri if Sat)
    - Martin Luther King Jr. Day (3rd Mon in Jan)
    - Washington's Birthday / Presidents Day (3rd Mon in Feb)
    - Good Friday (Western Easter - 2 days)
    - Memorial Day (Last Mon in May)
    - Juneteenth National Independence Day (Jun 19, observed Mon if Sun, Fri if Sat; since 2021)
    - Independence Day (Jul 4, observed Mon if Sun, Fri if Sat)
    - Labor Day (1st Mon in Sep)
    - Thanksgiving Day (4th Thu in Nov)
    - Christmas Day (Dec 25, observed Mon if Sun, Fri if Sat)
    """
    year = d.year

    def _observed(month: int, day: int) -> date:
        dt = date(year, month, day)
        if dt.weekday() == 5:  # Saturday -> Friday
            return date(year, month, day - 1)
        if dt.weekday() == 6:  # Sunday -> Monday
            return date(year, month, day + 1)
        return dt

    if d == _observed(1, 1):
        return True
    if year >= 2021 and d == _observed(6, 19):
        return True
    if d == _observed(7, 4):
        return True
    if d == _observed(12, 25):
        return True

    # MLK Day: 3rd Monday in January
    if d.month == 1 and d.weekday() == 0 and 15 <= d.day <= 21:
        return True
    # Presidents Day: 3rd Monday in February
    if d.month == 2 and d.weekday() == 0 and 15 <= d.day <= 21:
        return True
    # Memorial Day: Last Monday in May
    if d.month == 5 and d.weekday() == 0 and d.day >= 25:
        return True
    # Labor Day: 1st Monday in September
    if d.month == 9 and d.weekday() == 0 and d.day <= 7:
        return True
    # Thanksgiving: 4th Thursday in November
    if d.month == 11 and d.weekday() == 3 and 22 <= d.day <= 28:
        return True

    # Good Friday (computus algorithm for Western Easter)
    a = year % 19
    b = year // 100
    c = year % 100
    d_c = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d_c - g + 15) % 30
    i = c // 4
    k = c % 4
    comp_l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * comp_l) // 451
    month = (h + comp_l - 7 * m + 114) // 31
    day = ((h + comp_l - 7 * m + 114) % 31) + 1
    easter = date(year, month, day)
    good_friday = easter - timedelta(days=2)
    if d == good_friday:
        return True

    return False


def prior_business_day(d: date) -> date:
    """Return the prior business trading day before d, stepping past weekends & holidays.

    Under US T+1 settlement rules (SEC Rule 15c6-1 effective May 28, 2024),
    every trade executed on day T settles on the next business trading day S = T + 1.
    Given settlement date S, trade date T is exactly prior_business_day(S).
    """
    cur = d - timedelta(days=1)
    while cur.weekday() >= 5 or is_us_market_holiday(cur):
        cur -= timedelta(days=1)
    return cur


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
    date_source: str = "document"     # "document" | "derived_settle_t1"

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
    # Files or fills dropped because they are duplicates (daily confirmation re-downloads
    # or statement transactions already covered by confirmation). Reported, never silent.
    duplicates: list[dict] = field(default_factory=list)

    def summary(self) -> str:
        opts = sum(1 for f in self.fills if f.asset_type == "option")
        dup_files = sum(
            1
            for d in self.duplicates
            if "duplicate download" in d.get("why", "")
            or "partial duplicate" in d.get("why", "")
        )
        dup_fills = len(self.duplicates) - dup_files
        dup_parts = []
        if dup_files:
            dup_parts.append(f"{dup_files} duplicate files dropped")
        if dup_fills:
            dup_parts.append(f"{dup_fills} duplicate statement fills dropped")
        dup_str = f", {', '.join(dup_parts)}" if dup_parts else ""
        return (
            f"{self.files_read} files, {len(self.fills)} fills "
            f"({opts} option / {len(self.fills) - opts} equity), "
            f"{len(self.unparsed)} unparsed{dup_str}"
        )


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


def parse_statement_transactions(text: str, source_file: str = "") -> ParseReport:
    """Extract every executed fill from a monthly statement's Transaction Details (T108b)."""
    year = None
    if source_file:
        ym = re.search(r"20\d\d", source_file)
        if ym:
            year = int(ym.group(0))
    if year is None:
        for line in text.splitlines()[:20]:
            if "statement period" in line.lower() or "period" in line.lower():
                ym = re.search(r"\b(20\d\d)\b", line)
                if ym:
                    year = int(ym.group(1))
                    break
    if year is None:
        ym = re.search(r"\b(20\d\d)\b", text[:1000])
        if ym:
            year = int(ym.group(1))
        else:
            year = datetime.now().year

    lines = text.splitlines()
    in_td = False
    cur_settle_date = None
    fills: list[ParsedFill] = []
    unparsed: list[dict] = []

    for i, line in enumerate(lines):
        if re.search(r"Transaction\s+Details", line, re.IGNORECASE):
            in_td = True
            continue
        if not in_td:
            continue
        if _STMT_END_SECTION.search(line):
            in_td = False
            continue
        if any(s in line for s in _STMT_SKIP_LINE):
            continue

        dm = _STMT_SETTLE_DATE.match(line)
        if dm:
            try:
                m_num, d_num = int(dm.group(1)), int(dm.group(2))
                cur_settle_date = date(year, m_num, d_num)
            except ValueError:
                cur_settle_date = None

        act_m = _STMT_ACTION.search(line)
        if not act_m:
            continue

        if cur_settle_date is None:
            unparsed.append({
                "file": source_file,
                "line": line.strip()[:80],
                "why": "transaction row without settle date",
            })
            continue

        action = act_m.group("action")
        side = "buy" if action.lower() in {"purchase", "bought"} else "sell"

        # Build continuation window (up to 2 lines)
        window = [line[act_m.end():]]
        for k in range(1, 3):
            if i + k < len(lines):
                next_line = lines[i + k]
                if not re.search(
                    r"\b(Purchase|Sale|Expired|Assigned|Exercised|Deposit|Withdrawal|"
                    r"Other\s+Activity|Beginning\s+Cash|Pending)\b",
                    next_line,
                ) and not _STMT_SETTLE_DATE.match(next_line):
                    window.append(next_line)
                else:
                    break
        win_text = " ".join(window)

        # Symbol
        tokens = line[act_m.end():].split()
        sym = ""
        for t in tokens:
            t_clean = t.strip(".,;:()")
            if re.fullmatch(r"[A-Z]{1,6}", t_clean) and t_clean not in {
                "CALL", "PUT", "EXP", "ADR", "ETF", "F", "C", "P", "SHORT", "LONG"
            }:
                sym = t_clean
                break
        if not sym:
            unparsed.append({
                "file": source_file,
                "line": line.strip()[:80],
                "why": "could not extract symbol from statement row",
            })
            continue

        # Numbers
        num_matches = list(_STMT_QTY_PRICE.finditer(line[act_m.end():]))
        qp_matches = [m for m in num_matches if re.search(r"\.\d{4}", m.group(0))]
        if len(qp_matches) >= 2:
            qty_str = qp_matches[0].group("val").replace(",", "")
            price_str = qp_matches[1].group("val").replace(",", "")
            try:
                qty = float(qty_str)
                price = float(price_str)
            except ValueError:
                unparsed.append({
                    "file": source_file,
                    "line": line.strip()[:80],
                    "why": "quantity or price not numeric",
                })
                continue
        elif len(qp_matches) == 1:
            idx = num_matches.index(qp_matches[0])
            try:
                qty = float(qp_matches[0].group("val").replace(",", ""))
                if idx + 1 < len(num_matches):
                    price = float(num_matches[idx + 1].group("val").replace(",", ""))
                else:
                    unparsed.append({
                        "file": source_file,
                        "line": line.strip()[:80],
                        "why": "price column missing after quantity",
                    })
                    continue
            except ValueError:
                unparsed.append({
                    "file": source_file,
                    "line": line.strip()[:80],
                    "why": "quantity or price not numeric",
                })
                continue
        else:
            unparsed.append({
                "file": source_file,
                "line": line.strip()[:80],
                "why": "no 4-decimal quantity found in transaction row",
            })
            continue

        # Option detection
        opt_match = _OPTION.search(win_text)
        is_opt = bool(
            opt_match
            or re.search(r"\b(CALL|PUT)\b", win_text, re.IGNORECASE)
            or _OPTION_IDENTITY.search(win_text)
            or re.search(r"\bEXP\s+\d{2}/\d{2}/\d{2}\b", win_text)
        )
        asset_type = "option" if is_opt else "equity"

        exp = None
        strike = None
        right = None

        if is_opt:
            if opt_match:
                try:
                    exp = datetime.strptime(opt_match.group("expiry"), "%m/%d/%Y").date()
                    strike = float(opt_match.group("strike").replace(",", ""))
                    right = opt_match.group("right").lower()
                except ValueError:
                    pass
            if strike is None:
                sm = _OPTION_IDENTITY.search(win_text)
                if sm:
                    strike = float(sm.group("strike").replace(",", ""))
                    right = "put" if sm.group("letter").upper() == "P" else "call"
                else:
                    rm = re.search(r"\b(CALL|PUT)\b", win_text, re.IGNORECASE)
                    if rm:
                        right = rm.group(1).lower()
                    st_m = re.search(r"\$(\d+(?:\.\d+)?)", win_text)
                    if st_m:
                        strike = float(st_m.group(1))

            if exp is None:
                dm_full = _FULL_DATE.search(win_text)
                if dm_full:
                    try:
                        exp = datetime.strptime(dm_full.group(1), "%m/%d/%Y").date()
                    except ValueError:
                        exp = None
                if exp is None:
                    em_short = re.search(r"\bEXP\s+(\d{2}/\d{2}/\d{2})\b", win_text)
                    if em_short:
                        try:
                            exp = datetime.strptime(em_short.group(1), "%m/%d/%y").date()
                        except ValueError:
                            exp = None

            if strike is None or right is None or exp is None:
                unparsed.append({
                    "file": source_file,
                    "line": line.strip()[:80],
                    "why": (
                        f"incomplete option parameters for {sym} "
                        f"(exp={exp}, strike={strike}, right={right})"
                    ),
                })
                continue

        comm = 0.0
        cm = re.search(r"Commission\s*\$?(?P<comm>[\d.]+)", win_text)
        if cm:
            comm = float(cm.group("comm"))
        fee = 0.0
        fm = re.search(r"(?:IndustryFee|Industry\s+Fee|Charges)\s*\$?(?P<fee>[\d.]+)", win_text)
        if fm:
            fee = float(fm.group("fee"))

        # True trade date derived from settlement date under US T+1 settlement rules (D026/T108b)
        trade_date = prior_business_day(cur_settle_date)

        fills.append(ParsedFill(
            trade_date=trade_date,
            settle_date=cur_settle_date,
            symbol=sym,
            side=side,
            qty=qty,
            price=price,
            description=re.sub(r"\s{2,}", " ", win_text)[:120],
            asset_type=asset_type,
            commission=round(comm, 4),
            fees=round(fee, 4),
            option_expiry=exp,
            option_strike=strike,
            option_right=right,
            source_file=source_file,
            date_source="derived_settle_t1",
        ))

    return ParseReport(fills=fills, unparsed=unparsed, files_read=1)


def _fill_matches_trade(sf: ParsedFill, cf: ParsedFill) -> bool:
    """True if statement fill sf corresponds to confirmation fill cf (or another statement fill)."""
    if sf.symbol != cf.symbol:
        return False
    if sf.side != cf.side:
        return False
    if sf.asset_type != cf.asset_type:
        return False
    if abs(sf.qty - cf.qty) > 1e-4:
        return False
    if abs(sf.price - cf.price) > 1e-3:
        return False
    if sf.asset_type == "option":
        if sf.option_right != cf.option_right:
            return False
        if abs((sf.option_strike or 0.0) - (cf.option_strike or 0.0)) > 0.005:
            return False
        if sf.option_expiry != cf.option_expiry:
            return False
    # Date comparison: matches on trade_date or settlement window (within 4 calendar days)
    if sf.trade_date == cf.trade_date:
        return True
    settle = sf.settle_date or sf.trade_date
    conf_settle = cf.settle_date or cf.trade_date
    if abs((cf.trade_date - settle).days) <= 4 or abs((sf.trade_date - conf_settle).days) <= 4:
        return True
    return False


def dedupe_statement_fills(
    conf_reports: list[ParseReport], stmt_reports: list[ParseReport]
) -> list[ParseReport]:
    """Merge confirmation fills and statement fills without double-counting (T108b).

    Cross-source deduplication rules:
    1. A statement fill that matches an unused confirmation fill is dropped as duplicate.
    2. A statement fill that matches an already-kept statement fill from an earlier statement
       (e.g., pending trade appearing on month M statement and settled on month M+1 statement)
       is dropped as duplicate.
    3. A statement fill that matches an already-consumed confirmation fill is dropped as duplicate.
    """
    kept_conf_reports = dedupe_daily_documents(conf_reports)
    all_conf_fills = [f for r in kept_conf_reports for f in r.fills]

    kept_stmt_reports: list[ParseReport] = []
    used_conf_indices: set[int] = set()
    accepted_stmt_fills: list[ParsedFill] = []

    for r in stmt_reports:
        kept_fills: list[ParsedFill] = []
        duplicates: list[dict] = list(r.duplicates)
        for sf in r.fills:
            # 1. Match against unused confirmation fills
            matched_conf_idx = None
            for idx, cf in enumerate(all_conf_fills):
                if idx not in used_conf_indices and _fill_matches_trade(sf, cf):
                    matched_conf_idx = idx
                    break
            if matched_conf_idx is not None:
                used_conf_indices.add(matched_conf_idx)
                duplicates.append({
                    "file": sf.source_file,
                    "why": (
                        f"statement fill {sf.symbol} {sf.side} {sf.qty}@{sf.price} on "
                        f"{sf.trade_date} covered by confirmation from "
                        f"{all_conf_fills[matched_conf_idx].source_file}"
                    ),
                })
                continue

            # 2. Match against already-kept statement fills
            # (cross-statement duplicate / month-boundary)
            matched_stmt = None
            for prev_sf in accepted_stmt_fills:
                if _fill_matches_trade(sf, prev_sf):
                    matched_stmt = prev_sf
                    break
            if matched_stmt is not None:
                duplicates.append({
                    "file": sf.source_file,
                    "why": (
                        f"statement fill {sf.symbol} {sf.side} {sf.qty}@{sf.price} on "
                        f"{sf.trade_date} already imported from statement "
                        f"{matched_stmt.source_file}"
                    ),
                })
                continue

            # 3. Match against already-used confirmation fills (month boundary copy)
            matched_used_conf = None
            for idx in used_conf_indices:
                cf = all_conf_fills[idx]
                if _fill_matches_trade(sf, cf):
                    matched_used_conf = cf
                    break
            if matched_used_conf is not None:
                duplicates.append({
                    "file": sf.source_file,
                    "why": (
                        f"statement fill {sf.symbol} {sf.side} {sf.qty}@{sf.price} on "
                        f"{sf.trade_date} duplicate copy of confirmation fill from "
                        f"{matched_used_conf.source_file}"
                    ),
                })
                continue

            # Unique new fill: keep it
            kept_fills.append(sf)
            accepted_stmt_fills.append(sf)

        kept_stmt_reports.append(ParseReport(
            fills=kept_fills,
            unparsed=r.unparsed,
            files_read=r.files_read,
            duplicates=duplicates,
        ))

    return kept_conf_reports + kept_stmt_reports


def merge(reports: list[ParseReport]) -> ParseReport:
    out = ParseReport(files_read=sum(r.files_read for r in reports))
    for r in reports:
        out.fills.extend(r.fills)
        out.unparsed.extend(r.unparsed)
        out.duplicates.extend(r.duplicates)
    out.fills.sort(key=lambda f: (f.trade_date, f.symbol, 0 if f.side == "buy" else 1))
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
    """Parse a single trade confirmation or monthly statement file (.txt or .pdf)."""
    p = Path(path)
    if not p.exists():
        return ParseReport(
            unparsed=[{"file": str(p), "why": "file does not exist"}],
            files_read=0,
        )

    if p.suffix.lower() in {".txt", ".text"}:
        text = p.read_text(encoding="utf-8", errors="replace")
        if is_monthly_statement(text, source_file=p.name):
            return parse_statement_transactions(text, source_file=p.name)
        return parse_confirmation(text, source_file=p.name)

    if p.suffix.lower() == ".pdf":
        try:
            text = extract_pdf_text(p)
            if is_monthly_statement(text, source_file=p.name):
                return parse_statement_transactions(text, source_file=p.name)
            return parse_confirmation(text, source_file=p.name)
        except ImportError:
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
                if is_monthly_statement(text, source_file=p.name):
                    return parse_statement_transactions(text, source_file=p.name)
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
        if is_monthly_statement(text, source_file=p.name):
            return parse_statement_transactions(text, source_file=p.name)
        return parse_confirmation(text, source_file=p.name)
    except Exception as e:
        return ParseReport(
            unparsed=[{"file": p.name, "why": f"read error ({e})"}],
            files_read=1,
        )


def parse_directory(dir_path: str | Path) -> ParseReport:
    """Parse all trade confirmations and monthly statements (.txt and .pdf) in a directory."""
    p = Path(dir_path)
    if not p.exists() or not p.is_dir():
        return ParseReport(files_read=0)

    conf_reports: list[ParseReport] = []
    stmt_reports: list[ParseReport] = []
    for item in sorted(p.iterdir()):
        if item.is_file() and item.suffix.lower() in {".txt", ".pdf"}:
            try:
                if item.suffix.lower() == ".pdf":
                    text = extract_pdf_text(item)
                else:
                    text = item.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                conf_reports.append(ParseReport(
                    unparsed=[{"file": item.name, "why": f"read error ({e})"}],
                    files_read=1,
                ))
                continue

            if is_monthly_statement(text, source_file=item.name):
                stmt_reports.append(parse_statement_transactions(text, source_file=item.name))
            else:
                conf_reports.append(parse_confirmation(text, source_file=item.name))

    if not conf_reports and not stmt_reports:
        return ParseReport(files_read=0)
    if stmt_reports and conf_reports:
        return merge(dedupe_statement_fills(conf_reports, stmt_reports))
    if stmt_reports:
        return merge(stmt_reports)
    return merge(dedupe_daily_documents(conf_reports))
