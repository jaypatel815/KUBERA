"""Pre-trade pattern warnings (T104, D026).

Evaluates a proposed trade setup against the trader's historical execution
record (fills from statement confirmations or broker transactions) to identify
recurring behavioral pitfalls or historical negative-expectancy setups before
an order is placed.

Key principles (D026):
  1. Pure descriptive history: Describes what happened historically, never predicts
     or promises future outcomes.
  2. Sample-size rigor (N): Every pattern finding carries its exact sample size (N).
  3. Insufficient sample fail-closed: Refuses to assert patterns when sample size
     is below statistical thresholds (MIN_SAMPLE = 3).
  4. Asset class segregation: Sizing and pace comparisons never cross asset class
     boundaries (equity notionals are never compared to option premiums).
  5. Deterministic arithmetic: Pure functions in /backend/analysis, no LLM math.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Sequence

from analysis.attribution import OPTION_MULTIPLIER
from analysis.autopsy import (
    DAYS_OF_WEEK,
    AutopsyRoundTrip,
    match_fifo_trips,
    normalize_fill,
)
from analysis.risk_tolerance import (
    REACTION_WINDOW_HOURS,
    REVENGE_SIZING_RATIO,
)

MIN_SAMPLE_GENERAL = 3
MIN_SAMPLE_DAY_OF_WEEK = 5
OCC_OPTION_RE = re.compile(r"^([A-Z]{1,6})(\d{6})([CP])(\d{8})$")


@dataclass(frozen=True)
class ProposedTrade:
    """A planned or contemplated trade setup to be evaluated against history."""

    symbol: str
    action: str = "buy"                         # "buy" | "sell" | "short" | "cover"
    asset_type: str = "equity"                  # "equity" | "option"
    qty: float | None = None
    price: float | None = None
    notional: float | None = None               # explicit dollar exposure
    option_expiry: date | None = None
    option_strike: float | None = None
    option_right: str | None = None             # "call" | "put"
    dte: int | None = None                      # days to expiration (0 = 0DTE)
    asof: datetime | None = None                # evaluation timestamp (defaults to now UTC)

    @property
    def clean_symbol(self) -> str:
        """Extract underlying symbol if this is an OCC option symbol."""
        s = self.symbol.strip().upper()
        m = OCC_OPTION_RE.match(s)
        if m:
            return m.group(1)
        return s

    @property
    def is_0dte(self) -> bool:
        if self.asset_type != "option":
            return False
        if self.dte is not None:
            return self.dte == 0
        if self.option_expiry and self.asof:
            return self.option_expiry == self.asof.date()
        return False

    @property
    def estimated_notional(self) -> float | None:
        if self.notional is not None:
            return round(self.notional, 2)
        if self.qty is not None and self.price is not None:
            mult = OPTION_MULTIPLIER if self.asset_type == "option" else 1
            return round(self.qty * self.price * mult, 2)
        return None


@dataclass(frozen=True)
class PatternWarning:
    """A single identified pattern or setup observation with supporting evidence."""

    category: str
    severity: str                               # "high" | "medium" | "caution" | "info"
    headline: str
    sample_size: int
    evidence: dict[str, Any]
    narrative: str


@dataclass(frozen=True)
class PatternWarningReport:
    """Comprehensive pre-trade pattern warning assessment."""

    symbol: str
    underlying: str
    proposed_action: str
    asset_type: str
    proposed_notional: float | None
    is_0dte: bool
    warnings: list[PatternWarning]
    warnings_count: int
    has_high_severity: bool
    historical_trips_count: int
    verdict: str
    narrative: list[str]
    caveats: list[str]
    asof: datetime
    note: str = (
        "Pre-trade pattern warnings are descriptive observations computed from your "
        "historical trade executions (D026). Every finding includes exact sample size (N). "
        "This tool describes past behavior — it does not predict future price movement."
    )


def normalize_proposed_trade(p: ProposedTrade | dict[str, Any]) -> ProposedTrade:
    """Ensure ProposedTrade has parsed OCC symbols, asset types, DTE, and timestamps."""
    if isinstance(p, ProposedTrade):
        trade = p
    else:
        sym = str(p.get("symbol", "")).strip().upper()
        act = str(p.get("action", "buy")).strip().lower()
        is_occ = bool(OCC_OPTION_RE.match(sym))
        atype = str(p.get("asset_type") or ("option" if is_occ else "equity")).strip().lower()
        qty = float(p["qty"]) if p.get("qty") is not None else None
        prc = float(p["price"]) if p.get("price") is not None else None
        notional = float(p["notional"]) if p.get("notional") is not None else None
        exp = p.get("option_expiry")
        if isinstance(exp, str):
            try:
                exp = date.fromisoformat(exp)
            except ValueError:
                exp = None
        strike = float(p["option_strike"]) if p.get("option_strike") is not None else None
        right = str(p["option_right"]).lower() if p.get("option_right") else None
        dte = int(p["dte"]) if p.get("dte") is not None else None
        raw_asof = p.get("asof")
        if isinstance(raw_asof, datetime):
            asof = raw_asof if raw_asof.tzinfo else raw_asof.replace(tzinfo=timezone.utc)
        else:
            asof = datetime.now(timezone.utc)
        trade = ProposedTrade(
            symbol=sym,
            action=act,
            asset_type=atype,
            qty=qty,
            price=prc,
            notional=notional,
            option_expiry=exp,
            option_strike=strike,
            option_right=right,
            dte=dte,
            asof=asof,
        )

    m = OCC_OPTION_RE.match(trade.symbol)
    if m:
        raw_date = m.group(2)
        r_char = m.group(3)
        raw_strike = m.group(4)
        try:
            exp = date(2000 + int(raw_date[0:2]), int(raw_date[2:4]), int(raw_date[4:6]))
        except ValueError:
            exp = trade.option_expiry
        strike = float(raw_strike) / 1000.0
        right = "call" if r_char == "C" else "put"
        asof = trade.asof or datetime.now(timezone.utc)
        dte = (exp - asof.date()).days if exp else trade.dte
        return ProposedTrade(
            symbol=trade.symbol,
            action=trade.action,
            asset_type="option",
            qty=trade.qty,
            price=trade.price,
            notional=trade.notional,
            option_expiry=exp,
            option_strike=strike,
            option_right=right,
            dte=dte,
            asof=asof,
        )

    asof = trade.asof or datetime.now(timezone.utc)
    dte = trade.dte
    if dte is None and trade.option_expiry:
        dte = (trade.option_expiry - asof.date()).days

    return ProposedTrade(
        symbol=trade.symbol,
        action=trade.action,
        asset_type=trade.asset_type,
        qty=trade.qty,
        price=trade.price,
        notional=trade.notional,
        option_expiry=trade.option_expiry,
        option_strike=trade.option_strike,
        option_right=trade.option_right,
        dte=dte,
        asof=asof,
    )


def evaluate_pattern_warnings(
    fills_or_trips: Sequence[Any],
    proposed: ProposedTrade | dict[str, Any],
) -> PatternWarningReport:
    """Evaluate a proposed trade against historical fills/round-trips."""
    trade = normalize_proposed_trade(proposed)
    asof = trade.asof or datetime.now(timezone.utc)

    if fills_or_trips and isinstance(fills_or_trips[0], AutopsyRoundTrip):
        trips: list[AutopsyRoundTrip] = list(fills_or_trips)
    else:
        fills = [normalize_fill(f) for f in fills_or_trips]
        trips = match_fifo_trips(fills)

    warnings: list[PatternWarning] = []
    narrative_points: list[str] = []
    caveats: list[str] = []

    if len(trips) < MIN_SAMPLE_GENERAL:
        caveats.append(
            f"Historical record contains only {len(trips)} completed round trip(s). "
            f"At least {MIN_SAMPLE_GENERAL} completed trades are required for pattern evaluation."
        )
        return PatternWarningReport(
            symbol=trade.symbol,
            underlying=trade.clean_symbol,
            proposed_action=trade.action,
            asset_type=trade.asset_type,
            proposed_notional=trade.estimated_notional,
            is_0dte=trade.is_0dte,
            warnings=[],
            warnings_count=0,
            has_high_severity=False,
            historical_trips_count=len(trips),
            verdict="insufficient_history",
            narrative=[
                f"Insufficient historical data ({len(trips)} completed trades, "
                f"minimum {MIN_SAMPLE_GENERAL} required) to identify personal trade setup patterns."
            ],
            caveats=caveats,
            asof=asof,
        )

    sorted_trips = sorted(trips, key=lambda t: t.exit_ts)

    # ------------------------------------------------ Check 1: 0DTE / Ultra-short Options
    if trade.asset_type == "option" and trade.is_0dte:
        dte0_trips = [t for t in sorted_trips if t.is_0dte]
        n_dte0 = len(dte0_trips)
        if n_dte0 >= MIN_SAMPLE_GENERAL:
            dte0_wins = [t for t in dte0_trips if t.pnl > 0]
            dte0_losses = [t for t in dte0_trips if t.pnl < 0]
            dte0_pnl = round(sum(t.pnl for t in dte0_trips), 2)
            dte0_win_rate = round(len(dte0_wins) / n_dte0, 3)
            avg_w = (
                round(sum(t.pnl for t in dte0_wins) / len(dte0_wins), 2)
                if dte0_wins else 0.0
            )
            avg_l = (
                round(sum(t.pnl for t in dte0_losses) / len(dte0_losses), 2)
                if dte0_losses else 0.0
            )

            if dte0_pnl < 0 or dte0_win_rate < 0.50:
                sev = "high" if (dte0_win_rate < 0.40 or dte0_pnl < -1000) else "medium"
                msg = (
                    f"Historically on 0DTE options, you have executed {n_dte0} round trips with a "
                    f"{dte0_win_rate:.1%} win rate ({len(dte0_wins)}W / {len(dte0_losses)}L) and "
                    f"${dte0_pnl:,.2f} total realized P&L (avg loss ${avg_l:,.2f} vs "
                    f"avg win ${avg_w:,.2f})."
                )
                warnings.append(
                    PatternWarning(
                        category="0dte_risk",
                        severity=sev,
                        headline=(
                            f"0DTE option trade matches a historical pattern of negative "
                            f"expectancy (${dte0_pnl:,.2f} P&L across {n_dte0} trades)."
                        ),
                        sample_size=n_dte0,
                        evidence={
                            "round_trips": n_dte0,
                            "wins": len(dte0_wins),
                            "losses": len(dte0_losses),
                            "win_rate": dte0_win_rate,
                            "total_realized_pnl": dte0_pnl,
                            "avg_win": avg_w,
                            "avg_loss": avg_l,
                        },
                        narrative=msg,
                    )
                )
                narrative_points.append(msg)
        else:
            caveats.append(
                f"Proposed trade is 0DTE, but historical record has only {n_dte0} "
                f"0DTE round trip(s) (N < {MIN_SAMPLE_GENERAL})."
            )

    # ------------------------------------------------ Check 2: Revenge Sizing Drift After Losses
    last_trip = sorted_trips[-1] if sorted_trips else None
    if last_trip and last_trip.pnl < 0:
        time_since_loss_hours = (asof - last_trip.exit_ts).total_seconds() / 3600.0
        is_recent_loss = (
            time_since_loss_hours <= REACTION_WINDOW_HOURS
            or asof.date() == last_trip.exit_ts.date()
        )

        if is_recent_loss:
            prop_notional = trade.estimated_notional
            asset_trips = [t for t in sorted_trips if t.asset_type == trade.asset_type]
            if asset_trips:
                notionals = sorted([
                    abs(t.qty * t.entry_price * t.contract_multiplier) for t in asset_trips
                ])
                med_idx = len(notionals) // 2
                baseline_median = notionals[med_idx]
            else:
                baseline_median = 0.0

            if prop_notional is not None and baseline_median > 0:
                sizing_ratio = prop_notional / baseline_median
                if sizing_ratio >= REVENGE_SIZING_RATIO:
                    # Count historical losses in this asset class followed by re-entry
                    reaction_win = timedelta(hours=REACTION_WINDOW_HOURS)
                    n_post_loss = sum(
                        1 for i, t in enumerate(asset_trips[:-1])
                        if t.pnl < 0 and any(
                            t.exit_ts < nxt.entry_ts <= t.exit_ts + reaction_win
                            for nxt in asset_trips[i + 1:]
                        )
                    )
                    msg = (
                        f"Your last closed trade was a loss (${last_trip.pnl:,.2f} on "
                        f"{last_trip.symbol}). Proposed {trade.asset_type} notional of "
                        f"${prop_notional:,.2f} is {sizing_ratio:.1f}x your historical "
                        f"median size (${baseline_median:,.2f})."
                    )
                    warnings.append(
                        PatternWarning(
                            category="sizing_drift",
                            severity="high",
                            headline=(
                                f"Revenge sizing alert: Proposed notional (${prop_notional:,.2f}) "
                                f"is {sizing_ratio:.1f}x typical size following a recent loss."
                            ),
                            sample_size=len(asset_trips),
                            evidence={
                                "last_loss_symbol": last_trip.symbol,
                                "last_loss_pnl": last_trip.pnl,
                                "proposed_notional": prop_notional,
                                "baseline_median_notional": baseline_median,
                                "sizing_ratio": round(sizing_ratio, 2),
                                "historical_post_loss_sample": n_post_loss,
                            },
                            narrative=msg,
                        )
                    )
                    narrative_points.append(msg)

            # ---------------------------------------- Check 3: Post-loss Rapid Tilt Tempo
            if time_since_loss_hours < 1.0 and len(asset_trips) >= MIN_SAMPLE_GENERAL:
                mins = time_since_loss_hours * 60.0
                msg = (
                    f"Rapid trade entry contemplated only {mins:.0f} minutes after a closed "
                    f"loss (${last_trip.pnl:,.2f} on {last_trip.symbol}). Fast re-entries after "
                    f"losses have historically been correlated with tilt pacing."
                )
                warnings.append(
                    PatternWarning(
                        category="post_loss_tempo",
                        severity="medium",
                        headline=(
                            f"Tilt tempo alert: Rapid trade contemplated {mins:.0f}m after "
                            f"a closed loss."
                        ),
                        sample_size=len(asset_trips),
                        evidence={
                            "last_loss_symbol": last_trip.symbol,
                            "last_loss_pnl": last_trip.pnl,
                            "minutes_since_loss": round(mins, 1),
                        },
                        narrative=msg,
                    )
                )
                narrative_points.append(msg)

    # ------------------------------------------------ Check 4: Symbol-Specific Track Record
    target_sym = trade.clean_symbol
    sym_trips = [t for t in sorted_trips if t.symbol == target_sym or t.symbol == trade.symbol]
    n_sym = len(sym_trips)
    if n_sym >= MIN_SAMPLE_GENERAL:
        sym_wins = [t for t in sym_trips if t.pnl > 0]
        sym_losses = [t for t in sym_trips if t.pnl < 0]
        sym_pnl = round(sum(t.pnl for t in sym_trips), 2)
        sym_win_rate = round(len(sym_wins) / n_sym, 3)
        sym_avg_w = (
            round(sum(t.pnl for t in sym_wins) / len(sym_wins), 2) if sym_wins else 0.0
        )
        sym_avg_l = (
            round(sum(t.pnl for t in sym_losses) / len(sym_losses), 2) if sym_losses else 0.0
        )

        if sym_pnl < 0 and sym_win_rate < 0.45:
            sev = "high" if sym_pnl < -2000 else "medium"
            msg = (
                f"Historically on {target_sym}, your record is {len(sym_wins)}W / "
                f"{len(sym_losses)}L ({sym_win_rate:.1%} win rate) across {n_sym} closed "
                f"round trips with ${sym_pnl:,.2f} total realized P&L (avg loss "
                f"${sym_avg_l:,.2f} vs avg win ${sym_avg_w:,.2f})."
            )
            warnings.append(
                PatternWarning(
                    category="symbol_history",
                    severity=sev,
                    headline=(
                        f"Historical negative expectancy on {target_sym} (${sym_pnl:,.2f} P&L, "
                        f"{sym_win_rate:.1%} win rate across {n_sym} trades)."
                    ),
                    sample_size=n_sym,
                    evidence={
                        "symbol": target_sym,
                        "round_trips": n_sym,
                        "wins": len(sym_wins),
                        "losses": len(sym_losses),
                        "win_rate": sym_win_rate,
                        "total_realized_pnl": sym_pnl,
                        "avg_win": sym_avg_w,
                        "avg_loss": sym_avg_l,
                    },
                    narrative=msg,
                )
            )
            narrative_points.append(msg)
    else:
        if n_sym > 0:
            caveats.append(
                f"Historical record contains only {n_sym} closed trade(s) on {target_sym} "
                f"(insufficient sample, minimum {MIN_SAMPLE_GENERAL} required)."
            )
        else:
            caveats.append(f"No prior closed trades on {target_sym} in historical record.")

    # ------------------------------------------------ Check 5: Day of Week Disadvantage
    day_idx = asof.weekday()
    day_name = DAYS_OF_WEEK[day_idx]
    day_trips = [t for t in sorted_trips if t.exit_ts.weekday() == day_idx]
    n_day = len(day_trips)
    if n_day >= MIN_SAMPLE_DAY_OF_WEEK:
        day_wins = [t for t in day_trips if t.pnl > 0]
        day_losses = [t for t in day_trips if t.pnl < 0]
        day_pnl = round(sum(t.pnl for t in day_trips), 2)
        day_win_rate = round(len(day_wins) / n_day, 3)

        if day_win_rate < 0.35 and day_pnl < 0:
            msg = (
                f"{day_name}s historically carry your lowest weekday performance: "
                f"{len(day_wins)}W / {len(day_losses)}L ({day_win_rate:.1%} win rate) across "
                f"{n_day} round trips with ${day_pnl:,.2f} total realized P&L."
            )
            warnings.append(
                PatternWarning(
                    category="day_of_week",
                    severity="caution",
                    headline=(
                        f"Weekday note: {day_name}s have historically produced a "
                        f"{day_win_rate:.1%} win rate (${day_pnl:,.2f} across {n_day} trades)."
                    ),
                    sample_size=n_day,
                    evidence={
                        "day": day_name,
                        "round_trips": n_day,
                        "wins": len(day_wins),
                        "losses": len(day_losses),
                        "win_rate": day_win_rate,
                        "total_realized_pnl": day_pnl,
                    },
                    narrative=msg,
                )
            )
            narrative_points.append(msg)

    # Determine overall verdict
    has_high = any(w.severity == "high" for w in warnings)
    has_med_or_caution = any(w.severity in ("medium", "caution") for w in warnings)

    if has_high:
        verdict = "warning_triggered"
    elif has_med_or_caution:
        verdict = "caution"
    else:
        verdict = "clear"
        narrative_points.append(
            f"No historical negative expectancy patterns or revenge sizing triggers detected "
            f"for this {trade.asset_type} setup across {len(trips)} completed round trips."
        )

    return PatternWarningReport(
        symbol=trade.symbol,
        underlying=trade.clean_symbol,
        proposed_action=trade.action,
        asset_type=trade.asset_type,
        proposed_notional=trade.estimated_notional,
        is_0dte=trade.is_0dte,
        warnings=warnings,
        warnings_count=len(warnings),
        has_high_severity=has_high,
        historical_trips_count=len(trips),
        verdict=verdict,
        narrative=narrative_points,
        caveats=caveats,
        asof=asof,
    )
