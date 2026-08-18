"""T016b — automated cross-check: Schwab API fills vs statement-parsed fills.

When reconcile_schwab.py was written, "the statement" existed only on paper, so
the human was the only possible check. The statement-parsed record has since
been audited against explicit statement rows (T108/T108b, 13/13 clean), which
makes an automated API-vs-parsed diff TWO INDEPENDENT SOURCES agreeing — not a
machine agreeing with itself. The human tick-off keeps the final word; this
module just does the bookkeeping.

The two sources genuinely differ in shape (owner-verified, 2026-08-17):
- The API is per-EXECUTION (one order can fill as 71 + 29), timestamps UTC.
  Statements are per-ORDER, one line per order at the qty-weighted price —
  his 71+29 @ 0.21 appeared as ONE line, $2,033.48 to the penny. So API fills
  are aggregated BY (order_id, symbol, side) before the join.
- API option fills carry the padded OCC symbol ("NVDA  260320C00177500");
  statement fills carry underlying + expiry/strike/right fields. Both are
  normalised to one key. An OCC symbol that will not parse is REPORTED
  (never guessed into an equity match).
- Statement trade dates are Eastern trading days; API times are UTC. The API
  side joins on its America/New_York date (T111) — the same convention that
  made all 83 measurable statement dates land exactly.

NEVER SILENTLY RECONCILE: every fill ends up in exactly one bucket — matched,
api_only, or statement_only — and near-misses (same instrument+side+qty,
date within a small window or price outside tolerance) are LABELLED for the
human, not absorbed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from analysis.market_time import MARKET_TZ

# One option contract = 100 shares; kept consistent with data.statements.
PRICE_TOL_DEFAULT = 0.01     # dollars; statement prints the weighted avg rounded
NEAR_DATE_WINDOW = 3         # days: how far apart a "near miss" date may be

_OCC = re.compile(r"^(?P<root>[A-Z.\/]{1,6})\s*(?P<ymd>\d{6})(?P<right>[CP])(?P<strike>\d{8})$")


def parse_occ(symbol: str) -> tuple[str, date, str, float] | None:
    """OCC symbol -> (underlying, expiry, right, strike); None if non-conforming.

    "NVDA  260320C00177500" -> ("NVDA", 2026-03-20, "call", 177.5)
    Fail-closed: a None is reported by the caller, never guessed around.
    """
    m = _OCC.match(symbol.strip().upper())
    if not m:
        return None
    ymd = m.group("ymd")
    try:
        expiry = date(2000 + int(ymd[0:2]), int(ymd[2:4]), int(ymd[4:6]))
    except ValueError:
        return None
    right = "call" if m.group("right") == "C" else "put"
    return m.group("root"), expiry, right, int(m.group("strike")) / 1000.0


def _instrument_key(underlying: str, asset_type: str,
                    expiry: date | None, right: str | None,
                    strike: float | None) -> tuple:
    if asset_type == "option":
        return ("option", underlying, expiry.isoformat() if expiry else "?",
                right or "?", round(strike or 0.0, 3))
    return ("equity", underlying)


@dataclass(frozen=True)
class OrderLine:
    """One comparable line — an aggregated API order or one statement row."""

    origin: str                  # "api" | "statement"
    trade_date: date             # Eastern trading day
    key: tuple                   # _instrument_key(...)
    side: str                    # "buy" | "sell"
    qty: float                   # CONTRACTS for options, shares for equity
    price: float                 # qty-weighted average for API orders
    label: str                   # human-readable: symbol + date + ids
    commission: float = 0.0
    fees: float = 0.0

    def describe(self) -> str:
        kind = self.key[0]
        name = self.key[1] if kind == "equity" else (
            f"{self.key[1]} {self.key[2]} {self.key[4]}{'C' if self.key[3] == 'call' else 'P'}")
        return (f"{self.trade_date} {self.side:4s} {self.qty:g} x {name} "
                f"@ {self.price:.4f} [{self.origin}: {self.label}]")


@dataclass
class CrossCheckReport:
    matched: list[tuple[OrderLine, OrderLine, str]] = field(default_factory=list)
    api_only: list[OrderLine] = field(default_factory=list)
    statement_only: list[OrderLine] = field(default_factory=list)
    near_misses: list[str] = field(default_factory=list)   # labelled, informational
    unparseable: list[dict] = field(default_factory=list)  # OCC symbols that failed

    @property
    def clean(self) -> bool:
        """True when every line on both sides found its counterpart and every
        symbol parsed. Near-misses keep clean False via their parent buckets."""
        return not (self.api_only or self.statement_only or self.unparseable)

    def summary(self) -> str:
        return (f"{len(self.matched)} matched, {len(self.api_only)} API-only, "
                f"{len(self.statement_only)} statement-only, "
                f"{len(self.near_misses)} near-miss note(s), "
                f"{len(self.unparseable)} unparseable")


def api_order_lines(fills) -> tuple[list[OrderLine], list[dict]]:
    """Aggregate per-execution API fills into per-order lines.

    Group by (order_id, symbol, side); qty is summed, price is qty-weighted —
    exactly the arithmetic that matched the owner's statement to the penny.
    Executions without an order_id stay single lines (their own group).
    """
    groups: dict[tuple, list] = {}
    bad: list[dict] = []
    for f in fills:
        gid = (f.order_id or f"exec-{id(f)}", f.symbol, f.side)
        groups.setdefault(gid, []).append(f)

    out: list[OrderLine] = []
    for (order_id, symbol, side), legs in groups.items():
        qty = sum(leg.qty for leg in legs)
        if qty <= 0:
            bad.append({"symbol": symbol, "why": "non-positive aggregated qty"})
            continue
        price = sum(leg.qty * leg.price for leg in legs) / qty
        et_date = min(
            leg.occurred_at.astimezone(MARKET_TZ).date() for leg in legs)
        is_option = str(getattr(legs[0], "fill_type", "") or "").lower() == "option"
        if is_option:
            parsed = parse_occ(symbol)
            if parsed is None:
                bad.append({"symbol": symbol,
                            "why": "option fill with unparseable OCC symbol"})
                continue
            underlying, expiry, right, strike = parsed
            key = _instrument_key(underlying, "option", expiry, right, strike)
        else:
            key = _instrument_key(symbol, "equity", None, None, None)
        out.append(OrderLine(
            origin="api", trade_date=et_date, key=key, side=side, qty=qty,
            price=round(price, 6),
            label=f"order {order_id}, {len(legs)} execution(s)",
            commission=round(sum(getattr(leg, "commission", 0.0) or 0.0 for leg in legs), 4),
            fees=round(sum(getattr(leg, "fees", 0.0) or 0.0 for leg in legs), 4),
        ))
    return out, bad


def statement_order_lines(parsed_fills) -> list[OrderLine]:
    """One statement Transaction-Details row -> one comparable line."""
    out = []
    for f in parsed_fills:
        key = _instrument_key(f.symbol, f.asset_type, f.option_expiry,
                              f.option_right, f.option_strike)
        out.append(OrderLine(
            origin="statement", trade_date=f.trade_date, key=key, side=f.side,
            qty=f.qty, price=f.price,
            label=f.source_file or "statement",
            commission=f.commission, fees=f.fees,
        ))
    return out


def _fee_note(a: OrderLine, s: OrderLine) -> str:
    """Informational only — never affects matching. Both sides now carry the
    broker's own numbers (T016c / T108b), so a disagreement is worth a line."""
    dc = abs(a.commission - s.commission)
    df = abs(a.fees - s.fees)
    if dc <= 0.02 and df <= 0.02:
        return "fees agree"
    return (f"FEE NOTE: commission api {a.commission:.2f} vs stmt "
            f"{s.commission:.2f}; fees api {a.fees:.2f} vs stmt {s.fees:.2f}")


def cross_check(api_fills, parsed_fills,
                price_tol: float = PRICE_TOL_DEFAULT) -> CrossCheckReport:
    """Join the two sources. Match = same Eastern date, same instrument key,
    same side, same qty, price within price_tol. Greedy 1:1 within a group so
    two identical same-day orders need two counterparts, not one reused."""
    if price_tol < 0:
        raise ValueError("price_tol must be >= 0")
    report = CrossCheckReport()
    api_lines, bad = api_order_lines(api_fills)
    report.unparseable.extend(bad)
    stmt_lines = statement_order_lines(parsed_fills)

    unmatched_stmt = list(stmt_lines)
    for a in sorted(api_lines, key=lambda x: (x.trade_date, x.key, x.side, x.qty)):
        hit = None
        for s in unmatched_stmt:
            if (s.trade_date == a.trade_date and s.key == a.key
                    and s.side == a.side and abs(s.qty - a.qty) < 1e-9
                    and abs(s.price - a.price) <= price_tol + 1e-12):
                hit = s
                break
        if hit is not None:
            unmatched_stmt.remove(hit)
            report.matched.append((a, hit, _fee_note(a, hit)))
        else:
            report.api_only.append(a)
    report.statement_only.extend(unmatched_stmt)

    # Near-miss labelling: same instrument+side+qty on both leftover sides,
    # date within the window OR price outside tolerance. Information for the
    # human — the lines STAY in their unmatched buckets.
    for a in report.api_only:
        for s in report.statement_only:
            if s.key != a.key or s.side != a.side or abs(s.qty - a.qty) > 1e-9:
                continue
            d = abs((s.trade_date - a.trade_date).days)
            price_ok = abs(s.price - a.price) <= price_tol
            if d == 0 and not price_ok:
                report.near_misses.append(
                    f"price differs by {abs(s.price - a.price):.4f} "
                    f"(tol {price_tol:.4f}): {a.describe()} vs {s.describe()}")
            elif 0 < d <= NEAR_DATE_WINDOW and price_ok:
                # price_ok required: without it this would claim "all else
                # equal" for pairs that ALSO disagree on price (D028 catch).
                report.near_misses.append(
                    f"dates {d} day(s) apart, all else equal: "
                    f"{a.describe()} vs {s.describe()}")
    return report
