"""T117 — tax-loss harvesting scan, MEASUREMENT ONLY (adopted methodology:
anthropics/financial-services wealth-management/tlh, Apache-2.0; our code).

What their checklist named that KUBERA lacked: a deliberate scan of open
lots for harvestable unrealized losses with the wash-sale windows worked
out. KUBERA has better raw material than the checklist assumes — REAL
recorded fills (T016c), FIFO open lots with entry clocks (T091b), live
prices — so the scan is deterministic end to end.

What is DELIBERATELY absent, with reasons:
- replacement-security suggestions: naming a specific buy is a
  recommendation; the D017 posture stands. The payload notes the CONCEPT
  (similar-exposure, not substantially identical) and stops there.
- tax-rate math: KUBERA does not know the owner's bracket. It reports the
  LOSS, never the refund. The $3,000 ordinary-income offset and
  carryforward exist as an informational note only.

NAMED LIMITATIONS carried on every scan (their checklist is RIGHT about
these and KUBERA cannot see them): wash sales span ALL household accounts
and DRIPs — KUBERA sees only the fills recorded in ITS database; options
lots are listed but unpriced on this feed. NOT TAX ADVICE — measurement
for a conversation with a tax professional.

Wash-sale mechanics implemented (30-day rule, IRC §1091 as commonly
summarized — the CONVENTION, not legal advice):
- LOOKBACK flag: a recorded BUY of the same symbol within the 30 days
  BEFORE a harvest sale would wash the loss — flagged with the buy date.
- FORWARD window: selling today starts a no-rebuy window through day +30;
  the payload gives the exact first safe repurchase date.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

LONG_TERM_DAYS = 365          # holding > this = long-term (the common line)
WASH_WINDOW_DAYS = 30

NOT_TAX_ADVICE = (
    "NOT TAX ADVICE - a measurement to bring to a tax professional. "
    "Wash-sale checks cover ONLY fills recorded in KUBERA's database: "
    "other household accounts, IRAs, and DRIPs are invisible here and CAN "
    "wash a loss this scan calls clean.")


@dataclass(frozen=True)
class HarvestCandidate:
    symbol: str
    qty: float
    entry_date: str | None           # None = lot has no recorded clock
    basis_price: float
    last_price: float | None         # None = unpriced (options on this feed)
    unrealized_pnl: float | None     # qty * mult * (last - basis); None unpriced
    term: str                        # "long" | "short" | "unknown"
    contract_multiplier: int
    wash_lookback_flag: str | None   # named buy that would wash a sale today
    no_rebuy_until: str              # first safe repurchase date if sold today
    note: str | None = None


@dataclass(frozen=True)
class TlhScan:
    asof_date: str
    candidates: list[HarvestCandidate] = field(default_factory=list)
    total_harvestable_loss: float = 0.0   # priced loss candidates only
    n_lots_scanned: int = 0
    n_unpriced: int = 0                   # listed, not silently dropped
    n_gains_skipped: int = 0
    limitations: str = NOT_TAX_ADVICE
    concept_note: str = (
        "replacement thinking (their checklist's sound idea, no names "
        "given): similar exposure without 'substantially identical' - an "
        "ETF on a DIFFERENT index generally qualifies; the same ticker "
        "rebought inside the window never does")


def _term(entry_date: str | None, today: date) -> str:
    if not entry_date:
        return "unknown"
    try:
        d = datetime.fromisoformat(str(entry_date).replace("Z", "+00:00")).date()
    except ValueError:
        return "unknown"
    return "long" if (today - d).days > LONG_TERM_DAYS else "short"


def scan_tlh(
    open_lots: list[dict],
    latest_prices: dict[str, float | None],
    recent_buys: list[tuple[str, str]],       # (symbol, ISO date) recorded buys
    today: date,
) -> TlhScan:
    """Pure scan over FIFO open lots. A lot is a CANDIDATE when its priced
    unrealized P&L is negative; gains are counted and skipped; unpriced
    lots (no last price - options on this feed) are LISTED as unpriced,
    never silently dropped and never guessed."""
    lookback_start = today - timedelta(days=WASH_WINDOW_DAYS)
    no_rebuy_until = (today + timedelta(days=WASH_WINDOW_DAYS + 1)).isoformat()

    buys_by_symbol: dict[str, list[str]] = {}
    for sym, d in recent_buys:
        try:
            bd = date.fromisoformat(str(d)[:10])
        except ValueError:
            continue
        if lookback_start <= bd <= today:
            buys_by_symbol.setdefault(sym.upper(), []).append(bd.isoformat())

    candidates: list[HarvestCandidate] = []
    total_loss = 0.0
    n_unpriced = n_gains = 0
    for lot in open_lots:
        sym = str(lot["symbol"]).upper()
        mult = int(lot.get("mult", 1))
        last = latest_prices.get(sym)
        entry_ts = lot.get("ts")
        entry_day = str(entry_ts)[:10] if entry_ts else None

        if last is None or last <= 0:
            n_unpriced += 1
            candidates.append(HarvestCandidate(
                symbol=sym, qty=lot["qty"], entry_date=entry_day,
                basis_price=lot["price"], last_price=None,
                unrealized_pnl=None, term=_term(entry_day, today),
                contract_multiplier=mult, wash_lookback_flag=None,
                no_rebuy_until=no_rebuy_until,
                note="unpriced on this feed - loss unknown, NOT assumed"))
            continue

        pnl = lot["qty"] * mult * (last - lot["price"])
        if pnl >= 0:
            n_gains += 1
            continue

        washes = buys_by_symbol.get(sym, [])
        flag = None
        if washes:
            flag = (f"recorded buy of {sym} on {min(washes)} is inside the "
                    f"{WASH_WINDOW_DAYS}-day lookback - selling this lot "
                    "today would WASH the loss")
        total_loss += pnl
        candidates.append(HarvestCandidate(
            symbol=sym, qty=lot["qty"], entry_date=entry_day,
            basis_price=lot["price"], last_price=last,
            unrealized_pnl=round(pnl, 2), term=_term(entry_day, today),
            contract_multiplier=mult, wash_lookback_flag=flag,
            no_rebuy_until=no_rebuy_until))

    # largest loss first - their checklist's prioritization, kept
    candidates.sort(key=lambda c: (c.unrealized_pnl is None,
                                   c.unrealized_pnl or 0.0))
    return TlhScan(
        asof_date=today.isoformat(),
        candidates=candidates,
        total_harvestable_loss=round(total_loss, 2),
        n_lots_scanned=len(open_lots),
        n_unpriced=n_unpriced,
        n_gains_skipped=n_gains,
    )
