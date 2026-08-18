"""T023b — fundamental ratios from FMP's free-tier statements (D030 #4).

Deterministic ratio arithmetic on statement rows the client already fetched.
Nothing here talks to the network; nothing here is an LLM's opinion.

Conventions, chosen and written down:
- FREE CASH FLOW: prefer the statement's OWN `freeCashFlow` when present (the
  T016c principle — the reporter's number beats our derivation). Otherwise
  derive OCF + capex, where FMP reports `capitalExpenditure` as a NEGATIVE
  outflow. A POSITIVE capex is a sign convention we have not observed — the
  year is REPORTED in `unparsed`, never silently "fixed" (T102 rule).
- FCF YIELD: latest fiscal year's FCF / current market cap (from /stable/
  profile). A backward-looking numerator over a live denominator — the note
  says so. None when either side is missing; never guessed.
- DEBT RATIOS: totalDebt / totalStockholdersEquity and totalDebt /
  totalAssets from the latest balance sheet. Negative equity is a real state
  (buyback-heavy names): debt_to_equity becomes None with a why, because a
  negative ratio reads as "low debt" to a skimming eye — the exact wrong
  conclusion.
- STALENESS: annual statements are stale by NATURE. Every reading carries its
  fiscal dates and an explicit note; the narration rules already forbid
  presenting stale data as current.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

STALENESS_NOTE = ("Annual statements: figures are as of each fiscal year-end, "
                  "NOT current. FCF yield divides last fiscal year's FCF by "
                  "TODAY's market cap.")


@dataclass(frozen=True)
class FcfYear:
    fiscal_date: str          # "2025-12-31"
    fcf: float
    source: str               # "reported" | "derived_ocf_plus_capex"


@dataclass(frozen=True)
class FundamentalsReading:
    symbol: str
    fcf_years: list[FcfYear] = field(default_factory=list)
    fcf_latest: float | None = None
    market_cap: float | None = None
    fcf_yield: float | None = None          # fcf_latest / market_cap
    debt_to_equity: float | None = None
    debt_to_assets: float | None = None
    balance_fiscal_date: str | None = None
    unparsed: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    asof: str = ""
    source: str = "fmp-free statements"


def _num(row: dict, *keys: str) -> float | None:
    for k in keys:
        v = row.get(k)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return float(v)
    return None


def _fcf_from_row(row: Any) -> FcfYear | dict:
    """One cash-flow-statement year -> FcfYear, or a reported-unparsed dict."""
    if not isinstance(row, dict):
        return {"why": "cash-flow row is not an object", "row": str(row)[:80]}
    fiscal = str(row.get("date") or row.get("fiscalDateEnding") or "").strip()
    if not fiscal:
        return {"why": "cash-flow row missing fiscal date — refusing to guess",
                "row": str(row)[:80]}
    reported = _num(row, "freeCashFlow")
    if reported is not None:
        return FcfYear(fiscal_date=fiscal, fcf=reported, source="reported")
    ocf = _num(row, "operatingCashFlow", "netCashProvidedByOperatingActivities")
    capex = _num(row, "capitalExpenditure")
    if ocf is None or capex is None:
        return {"why": "no freeCashFlow and cannot derive (missing OCF or capex)",
                "row": fiscal}
    if capex > 0:
        # FMP reports capex as a negative outflow; a positive value is an
        # unobserved sign convention. Report, don't guess (T102).
        return {"why": f"capex is POSITIVE ({capex:g}) — unobserved sign "
                       "convention, refusing to derive FCF", "row": fiscal}
    return FcfYear(fiscal_date=fiscal, fcf=ocf + capex,
                   source="derived_ocf_plus_capex")


def compose_fundamentals(symbol: str,
                         cash_flow_rows: list | None,
                         balance_rows: list | None,
                         market_cap: float | None) -> FundamentalsReading:
    """Pure composition. Every missing input degrades to None WITH a note."""
    notes: list[str] = [STALENESS_NOTE]
    unparsed: list[dict] = []

    years: list[FcfYear] = []
    for row in cash_flow_rows or []:
        out = _fcf_from_row(row)
        if isinstance(out, FcfYear):
            years.append(out)
        else:
            unparsed.append(out)
    years.sort(key=lambda y: y.fiscal_date, reverse=True)
    if cash_flow_rows is None:
        notes.append("cash-flow statements unavailable — no FCF computed")

    fcf_latest = years[0].fcf if years else None

    fcf_yield = None
    if fcf_latest is not None and market_cap is not None and market_cap > 0:
        fcf_yield = fcf_latest / market_cap
    elif fcf_latest is not None:
        notes.append("market cap unavailable — FCF computed, yield not")

    d2e = d2a = None
    balance_fiscal = None
    if balance_rows:
        bal = balance_rows[0] if isinstance(balance_rows[0], dict) else None
        if bal is None:
            unparsed.append({"why": "balance-sheet row is not an object",
                             "row": str(balance_rows[0])[:80]})
        else:
            balance_fiscal = str(bal.get("date") or "") or None
            debt = _num(bal, "totalDebt")
            equity = _num(bal, "totalStockholdersEquity", "totalEquity")
            assets = _num(bal, "totalAssets")
            if debt is not None and equity is not None:
                if equity > 0:
                    d2e = debt / equity
                else:
                    notes.append(
                        f"equity is non-positive ({equity:g}) — debt/equity "
                        "suppressed: a negative ratio reads as low debt, which "
                        "is the wrong conclusion")
            elif debt is None or equity is None:
                notes.append("balance sheet missing totalDebt or equity — "
                             "debt/equity not computed")
            if debt is not None and assets is not None and assets > 0:
                d2a = debt / assets
    else:
        notes.append("balance sheet unavailable — no debt ratios "
                     "(endpoint not yet probe-verified on this tier; "
                     "run scripts/fmp_check.py)")

    return FundamentalsReading(
        symbol=symbol.upper(),
        fcf_years=years,
        fcf_latest=fcf_latest,
        market_cap=market_cap,
        fcf_yield=round(fcf_yield, 6) if fcf_yield is not None else None,
        debt_to_equity=round(d2e, 4) if d2e is not None else None,
        debt_to_assets=round(d2a, 4) if d2a is not None else None,
        balance_fiscal_date=balance_fiscal,
        unparsed=unparsed,
        notes=notes,
        asof=datetime.now(timezone.utc).isoformat(),
    )
