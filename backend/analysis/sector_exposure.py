"""T065 — sector exposure measurement (needs T023's sector data; probe-OK).

MEASUREMENT, not enforcement: the by-sector weights and a loud warning when
one sector carries too much of the book. Hard sector CAPS would be a safety
rail, and rails only move through deliberate, owner-ratified limits (T061) —
so v1 measures and warns; a future ticket can wire ratified caps into the
engine the way the position cap already works.

Conventions:
- Weights are market_value / total book value (long-only book, D021).
- A symbol whose sector is UNKNOWN is grouped and REPORTED as "unknown" —
  never guessed into a sector, never dropped (T102).
- SECTOR_WARN_FRAC is a chosen tunable (commented): 40% of the book in one
  sector is concentration worth saying out loud, comfortably before it is
  a crisis.
"""

from __future__ import annotations

from dataclasses import dataclass, field

SECTOR_WARN_FRAC = 0.40   # tunable: warn when one sector holds this share


@dataclass(frozen=True)
class SectorExposure:
    by_sector: dict[str, float] = field(default_factory=dict)  # sector -> frac
    top_sector: str | None = None
    top_frac: float | None = None
    unknown_symbols: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    note: str = ("measurement only — sector CAPS would be a safety rail and "
                 "arrive only as owner-ratified limits (T061)")


def sector_exposure(positions: list[tuple[str, float]],
                    sectors: dict[str, str | None]) -> SectorExposure:
    """positions: (symbol, market_value); sectors: symbol -> sector or None."""
    total = sum(mv for _, mv in positions if mv > 0)
    if total <= 0:
        return SectorExposure(warnings=["no positive market value to measure"])

    by: dict[str, float] = {}
    unknown: list[str] = []
    for symbol, mv in positions:
        if mv <= 0:
            continue
        sector = sectors.get(symbol.upper()) or sectors.get(symbol)
        if not sector or not str(sector).strip():
            unknown.append(symbol.upper())
            sector = "unknown"
        key = str(sector).strip()
        by[key] = by.get(key, 0.0) + mv / total

    by = {k: round(v, 4) for k, v in sorted(by.items(), key=lambda kv: -kv[1])}
    top = next(iter(by), None)
    top_frac = by.get(top) if top else None

    warnings = []
    if top and top != "unknown" and top_frac and top_frac >= SECTOR_WARN_FRAC:
        warnings.append(
            f"{top_frac:.0%} of the book is {top} — one sector's bad day is "
            f"your bad day (warning line {SECTOR_WARN_FRAC:.0%})")
    if unknown:
        warnings.append(
            f"{len(unknown)} symbol(s) with no sector data grouped as "
            f"'unknown': {', '.join(sorted(unknown))} — their exposure is "
            "measured but unclassified")
    return SectorExposure(by_sector=by, top_sector=top, top_frac=top_frac,
                          unknown_symbols=sorted(unknown), warnings=warnings)
