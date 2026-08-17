"""Trading Autopsy (T103, D026).

Runs the full battery of behavioral, execution, and attribution diagnostics
over a trader's real fills (from statement confirmations or broker transactions):
  1. Instrument profile: options vs equities, 0DTE vs swing options, contracts vs shares.
  2. Holding period distribution (T091b): sub-day minutes/hours/same_day vs multi-day.
     Honest about date-only confirmations (never fabricating a clock or reporting 0.0h scalps).
  3. Behavioral tells (T069): sizing drift and tempo computed WITHIN asset class.
     Never mixing equity capital against option premium.
  4. Realized P&L, win rate, profit factor, payoff ratio, largest win/loss.
  5. Day-of-week and time-of-day execution distributions.
  6. Per-symbol performance & trade counts.
  7. Honest factual narrative points: every figure carries sample size (N),
     small samples state "insufficient", zero prediction.

Pure functions. Money math is deterministic and tested, never LLM-computed (AGENTS.md).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Sequence

from analysis.attribution import (
    OPTION_MULTIPLIER,
    _held_days,
)
from analysis.risk_tolerance import (
    MIN_PAIRED_OBSERVATIONS,
    MIN_TRIPS_FOR_BEHAVIOR,
    REACTION_WINDOW_HOURS,
    REVENGE_SIZING_RATIO,
    TILT_FREQUENCY_RATIO,
    sizing_drift,
)

DAYS_OF_WEEK = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


@dataclass(frozen=True)
class AutopsyFill:
    """Standardized fill representation for autopsy analysis."""

    symbol: str
    side: str                          # "buy" | "sell"
    qty: float
    price: float
    ts: datetime                       # tz-aware UTC or normalized datetime
    time_known: bool = True            # False if source is date-only (e.g. statement confirmation)
    asset_type: str = "equity"         # "equity" | "option"
    contract_multiplier: int = 1       # 100 for options, 1 for equity
    option_expiry: date | None = None
    option_strike: float | None = None
    option_right: str | None = None    # "put" | "call"
    description: str = ""
    source: str = ""

    @property
    def notional(self) -> float:
        """Total economic exposure."""
        return round(self.qty * self.price * self.contract_multiplier, 2)

    @property
    def is_0dte(self) -> bool:
        """True if option expires on the same calendar day as the trade."""
        if self.asset_type != "option" or not self.option_expiry:
            return False
        return self.option_expiry == self.ts.date()

    @property
    def contract_key(self) -> str:
        """Unique matching key for FIFO queues.
        Different option strikes/expiries on the same underlying must not mix."""
        if self.asset_type == "option" and self.option_expiry and self.option_strike:
            right = (self.option_right or "").upper()
            return f"{self.symbol}_{self.option_expiry.isoformat()}_{self.option_strike}_{right}"
        return self.symbol


@dataclass(frozen=True)
class AutopsyRoundTrip:
    """One completed round-trip slice from FIFO lot matching."""

    symbol: str
    contract_key: str
    asset_type: str
    qty: float
    entry_price: float
    exit_price: float
    pnl: float
    held_days: float | None
    entry_ts: datetime
    exit_ts: datetime
    is_0dte: bool
    time_known: bool
    contract_multiplier: int = 1
    # "sell" = a real closing fill; "expiry_assumed" = the lot's expiry passed
    # with no sell on record, so it is closed at exit 0 (T108/I026). The flag
    # exists so no consumer can mistake an assumption for an observation.
    closed_by: str = "sell"


@dataclass(frozen=True)
class InstrumentProfile:
    total_fills: int
    option_fills: int
    equity_fills: int
    option_pct: float
    dte0_fills: int
    dte0_pct_of_options: float | None
    calls_count: int
    puts_count: int
    total_notional: float
    option_notional: float
    equity_notional: float


@dataclass(frozen=True)
class PerformanceSummary:
    round_trips: int
    total_realized_pnl: float
    wins: int
    losses: int
    scratches: int
    win_rate: float | None
    profit_factor: float | None
    avg_win: float | None
    avg_loss: float | None
    payoff_ratio: float | None
    largest_win: float | None
    largest_loss: float | None
    option_realized_pnl: float
    equity_realized_pnl: float
    # T108: how much of the record is assumption rather than observation.
    expiry_assumed_count: int = 0
    expiry_assumed_pnl: float = 0.0


@dataclass(frozen=True)
class AssetBehavior:
    asset_type: str
    sizing_drift_ratio: float | None
    sizing_drift_sample: int
    sizing_drift_verdict: str
    post_loss_pace_ratio: float | None
    post_loss_pace_sample: int
    post_loss_pace_verdict: str


@dataclass(frozen=True)
class BehaviorSummary:
    options: AssetBehavior
    equities: AssetBehavior
    summary_verdict: str


@dataclass(frozen=True)
class TradingAutopsyReport:
    """Comprehensive Trading Autopsy Report (T103, D026)."""

    total_fills: int
    instrument_profile: InstrumentProfile
    performance: PerformanceSummary
    holding_periods: dict
    behavior: BehaviorSummary
    day_of_week_distribution: dict
    symbols: list[dict]
    narrative: list[str]
    caveats: list[str]
    note: str = (
        "Deterministic trading autopsy computed over executed fills. Every metric "
        "carries its sample count (N). Small sample sizes are marked 'insufficient'. "
        "Describes historical realized behavior only — zero predictions or promises."
    )


def normalize_fill(obj: Any) -> AutopsyFill:
    """Convert various fill types (ParsedFill, Fill, Transaction, dict) to AutopsyFill."""
    if isinstance(obj, AutopsyFill):
        return obj

    if isinstance(obj, dict):
        sym = str(obj.get("symbol", "")).upper()
        side = str(obj.get("side", "buy")).lower()
        qty = abs(float(obj.get("qty", 0.0)))
        price = float(obj.get("price", 0.0))
        raw_ts = obj.get("ts") or obj.get("occurred_at") or obj.get("trade_date")
        time_known = True
        if isinstance(raw_ts, datetime):
            ts = raw_ts if raw_ts.tzinfo else raw_ts.replace(tzinfo=timezone.utc)
            time_known = bool(obj.get("time_known", True))
        elif isinstance(raw_ts, date):
            ts = datetime.combine(raw_ts, time(0, 0), tzinfo=timezone.utc)
            time_known = False
        elif isinstance(raw_ts, str):
            try:
                ts = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
                if not ts.tzinfo:
                    ts = ts.replace(tzinfo=timezone.utc)
                # If only date format "YYYY-MM-DD"
                if len(raw_ts) == 10:
                    time_known = False
            except ValueError:
                ts = datetime.now(timezone.utc)
                time_known = False
        else:
            ts = datetime.now(timezone.utc)
            time_known = False

        asset_type = str(obj.get("asset_type") or obj.get("fill_type") or "equity").lower()
        default_mult = OPTION_MULTIPLIER if asset_type == "option" else 1
        mult = int(obj.get("contract_multiplier") or default_mult)
        exp = obj.get("option_expiry")
        if isinstance(exp, str):
            try:
                exp = date.fromisoformat(exp)
            except ValueError:
                exp = None
        strike = float(obj["option_strike"]) if obj.get("option_strike") is not None else None
        right = str(obj["option_right"]).lower() if obj.get("option_right") else None
        desc = str(obj.get("description", ""))
        src = str(obj.get("source", ""))
        return AutopsyFill(
            symbol=sym,
            side=side,
            qty=qty,
            price=price,
            ts=ts,
            time_known=time_known,
            asset_type=asset_type,
            contract_multiplier=mult,
            option_expiry=exp,
            option_strike=strike,
            option_right=right,
            description=desc,
            source=src,
        )

    # ParsedFill (data/statements.py) — confirmations carry trade_date only, no time of day
    if hasattr(obj, "trade_date") and hasattr(obj, "asset_type"):
        trade_d = getattr(obj, "trade_date")
        ts = datetime.combine(trade_d, time(0, 0), tzinfo=timezone.utc)
        asset_type = str(getattr(obj, "asset_type", "equity")).lower()
        mult = OPTION_MULTIPLIER if asset_type == "option" else 1
        return AutopsyFill(
            symbol=str(getattr(obj, "symbol")).upper(),
            side=str(getattr(obj, "side")).lower(),
            qty=abs(float(getattr(obj, "qty"))),
            price=float(getattr(obj, "price")),
            ts=ts,
            time_known=False,  # Schwab confirmation statements print date only
            asset_type=asset_type,
            contract_multiplier=mult,
            option_expiry=getattr(obj, "option_expiry", None),
            option_strike=getattr(obj, "option_strike", None),
            option_right=getattr(obj, "option_right", None),
            description=str(getattr(obj, "description", "")),
            source=str(getattr(obj, "source_file", "")),
        )

    # Transaction (data/models.py) or Fill (data/alpaca.py / data/schwab.py)
    sym = str(getattr(obj, "symbol", "")).upper()
    side = str(getattr(obj, "side", "buy")).lower()
    qty = abs(float(getattr(obj, "qty", 0.0)))
    price = float(getattr(obj, "price", 0.0))
    raw_ts = getattr(obj, "occurred_at", None) or getattr(obj, "asof", None)
    if isinstance(raw_ts, datetime):
        ts = raw_ts if raw_ts.tzinfo else raw_ts.replace(tzinfo=timezone.utc)
        time_known = True
    else:
        ts = datetime.now(timezone.utc)
        time_known = False

    fill_t = str(getattr(obj, "fill_type", getattr(obj, "asset_type", "equity"))).lower()
    asset_type = "option" if "option" in fill_t else "equity"
    mult = OPTION_MULTIPLIER if asset_type == "option" else 1
    return AutopsyFill(
        symbol=sym,
        side=side,
        qty=qty,
        price=price,
        ts=ts,
        time_known=time_known,
        asset_type=asset_type,
        contract_multiplier=mult,
        description=str(getattr(obj, "description", "")),
        source=str(getattr(obj, "source", "")),
    )


def match_fifo_trips(
    fills: Sequence[AutopsyFill],
    asof: date | None = None,
) -> list[AutopsyRoundTrip]:
    """FIFO lot matching per unique contract / equity symbol with contract multipliers.

    EXPIRY-AWARE (T108, I026): an option lot whose expiry has passed with no
    sell on record is a COMPLETED trade — the position no longer exists and the
    premium is gone — not an open position to be silently excluded. Before this,
    the matcher only ever saw SOLD lots, and since traders sell winners and let
    losers expire, every downstream number (win rate, P&L, pattern verdicts)
    carried survivorship bias. The owner caught it with one question: a 100%
    SPY-put win rate that was really ~$3,500 of invisible expired premium.

    Such lots close at exit 0.0 on the expiry date, flagged
    closed_by="expiry_assumed". Exit 0 is an ASSUMPTION — an in-the-money lot
    would have been auto-exercised, not expired worthless — which is why the
    flag exists and why scripts/reconcile_expiry.py cross-checks every assumed
    expiry against the monthly statements' explicit "Expired" rows.

    `asof` bounds "has expired": only expiries strictly BEFORE asof close
    (an option expiring today could still be sold today). Defaults to the
    current UTC date; tests pass it explicitly for determinism.
    """
    if asof is None:
        asof = datetime.now(timezone.utc).date()
    sorted_fills = sorted(fills, key=lambda f: (f.contract_key, f.ts, 0 if f.side == "buy" else 1))
    queues: dict[str, list[AutopsyFill]] = {}
    trips: list[AutopsyRoundTrip] = []

    for f in sorted_fills:
        q = queues.setdefault(f.contract_key, [])
        if f.side == "buy":
            q.append(f)
            continue

        # side == "sell": match against FIFO buys
        remaining = f.qty
        while remaining > 1e-9 and q:
            entry = q[0]
            take = min(remaining, entry.qty)
            pnl = round(take * (f.price - entry.price) * f.contract_multiplier, 2)
            both_time_known = entry.time_known and f.time_known
            if both_time_known:
                held = _held_days(entry.ts.isoformat(), f.ts.isoformat())
            else:
                # Date-only duration in full calendar days
                days_diff = (f.ts.date() - entry.ts.date()).days
                held = float(days_diff) if days_diff >= 0 else None

            trips.append(
                AutopsyRoundTrip(
                    symbol=f.symbol,
                    contract_key=f.contract_key,
                    asset_type=f.asset_type,
                    qty=take,
                    entry_price=entry.price,
                    exit_price=f.price,
                    pnl=pnl,
                    held_days=held,
                    entry_ts=entry.ts,
                    exit_ts=f.ts,
                    is_0dte=f.is_0dte,
                    time_known=both_time_known,
                    contract_multiplier=f.contract_multiplier,
                )
            )
            # Update remaining in the lot
            if take >= entry.qty - 1e-9:
                q.pop(0)
            else:
                # Replace with leftover portion
                q[0] = AutopsyFill(
                    symbol=entry.symbol,
                    side=entry.side,
                    qty=entry.qty - take,
                    price=entry.price,
                    ts=entry.ts,
                    time_known=entry.time_known,
                    asset_type=entry.asset_type,
                    contract_multiplier=entry.contract_multiplier,
                    option_expiry=entry.option_expiry,
                    option_strike=entry.option_strike,
                    option_right=entry.option_right,
                    description=entry.description,
                    source=entry.source,
                )
            remaining -= take

    # T108: close expired option lots that were never sold. Equity lots have no
    # expiry and genuinely-open options (expiry >= asof) stay open — only a lot
    # whose expiry is already in the past is a finished trade.
    for q in queues.values():
        for entry in q:
            if entry.asset_type != "option" or entry.option_expiry is None:
                continue
            if entry.option_expiry >= asof:
                continue
            exit_ts = datetime.combine(entry.option_expiry, time(0, 0), tzinfo=timezone.utc)
            days_diff = (entry.option_expiry - entry.ts.date()).days
            trips.append(
                AutopsyRoundTrip(
                    symbol=entry.symbol,
                    contract_key=entry.contract_key,
                    asset_type=entry.asset_type,
                    qty=entry.qty,
                    entry_price=entry.price,
                    exit_price=0.0,
                    pnl=round(entry.qty * (0.0 - entry.price) * entry.contract_multiplier, 2),
                    held_days=float(days_diff) if days_diff >= 0 else None,
                    entry_ts=entry.ts,
                    exit_ts=exit_ts,
                    is_0dte=entry.is_0dte,
                    # The expiry DATE is certain; the intraday moment is not.
                    time_known=False,
                    contract_multiplier=entry.contract_multiplier,
                    closed_by="expiry_assumed",
                )
            )

    # Chronological by exit. The pre-T108 order (grouped by contract key) was
    # an artifact of the queue walk that no consumer should have relied on.
    trips.sort(key=lambda t: (t.exit_ts, t.contract_key))
    return trips


def autopsy_holding_periods(trips: Sequence[AutopsyRoundTrip]) -> dict:
    """Holding period distribution that respects date-only vs timestamped fills."""
    by_bucket: dict[str, dict] = {
        "minutes": {"round_trips": 0, "wins": 0, "realized_pnl": 0.0, "win_rate": None},
        "hours": {"round_trips": 0, "wins": 0, "realized_pnl": 0.0, "win_rate": None},
        "same_day": {"round_trips": 0, "wins": 0, "realized_pnl": 0.0, "win_rate": None},
        "1-3d": {"round_trips": 0, "wins": 0, "realized_pnl": 0.0, "win_rate": None},
        "1-2wk": {"round_trips": 0, "wins": 0, "realized_pnl": 0.0, "win_rate": None},
        "2wk-1mo": {"round_trips": 0, "wins": 0, "realized_pnl": 0.0, "win_rate": None},
        "over_1mo": {"round_trips": 0, "wins": 0, "realized_pnl": 0.0, "win_rate": None},
        "unknown": {"round_trips": 0, "wins": 0, "realized_pnl": 0.0, "win_rate": None},
    }

    intraday_measured_count = 0
    same_day_unrecorded_count = 0
    measured_days_list: list[float] = []

    for t in trips:
        if t.held_days is None:
            bucket = "unknown"
        elif t.held_days >= 1.0:
            measured_days_list.append(t.held_days)
            if t.held_days < 3.0:
                bucket = "1-3d"
            elif t.held_days < 14.0:
                bucket = "1-2wk"
            elif t.held_days < 30.0:
                bucket = "2wk-1mo"
            else:
                bucket = "over_1mo"
        else:
            # Same calendar day (held_days < 1.0)
            if t.time_known and t.held_days > 0:
                intraday_measured_count += 1
                measured_days_list.append(t.held_days)
                if t.held_days < 1.0 / 24.0:
                    bucket = "minutes"
                elif t.held_days < 6.5 / 24.0:
                    bucket = "hours"
                else:
                    bucket = "same_day"
            else:
                # Same day, but time is not recorded on statement confirmation
                same_day_unrecorded_count += 1
                bucket = "same_day"

        slot = by_bucket[bucket]
        slot["round_trips"] += 1
        slot["realized_pnl"] = round(slot["realized_pnl"] + t.pnl, 2)
        if t.pnl > 0:
            slot["wins"] += 1

    for slot in by_bucket.values():
        if slot["round_trips"] > 0:
            slot["win_rate"] = round(slot["wins"] / slot["round_trips"], 4)

    median_days = None
    if measured_days_list:
        measured_days_list.sort()
        n = len(measured_days_list)
        median_days = (
            measured_days_list[n // 2]
            if n % 2
            else (measured_days_list[n // 2 - 1] + measured_days_list[n // 2]) / 2
        )
        median_days = round(median_days, 4)

    return {
        "by_bucket": by_bucket,
        "n_round_trips": len(trips),
        "intraday_measured_count": intraday_measured_count,
        "same_day_unrecorded_count": same_day_unrecorded_count,
        "median_days": median_days,
        "has_unrecorded_intraday_times": same_day_unrecorded_count > 0,
        "all_same_day_unrecorded": (
            same_day_unrecorded_count > 0 and intraday_measured_count == 0
        ),
    }


def analyze_asset_behavior(
    asset_type: str,
    trips: Sequence[AutopsyRoundTrip],
    fills: Sequence[AutopsyFill],
) -> AssetBehavior:
    """Analyze sizing drift and post-loss tempo strictly within a single asset class."""
    asset_trips = [t for t in trips if t.asset_type == asset_type]
    asset_fills = [f for f in fills if f.asset_type == asset_type]

    t_dicts = [
        {
            "pnl": t.pnl,
            "exit_ts": t.exit_ts.isoformat(),
            "entry_ts": t.entry_ts.isoformat(),
            "symbol": t.symbol,
        }
        for t in asset_trips
    ]
    f_dicts = [
        {
            "side": f.side,
            "ts_iso": f.ts.isoformat(),
            "qty": f.qty,
            "price": f.price * f.contract_multiplier,
        }
        for f in asset_fills
    ]

    drift_res = sizing_drift(t_dicts, f_dicts)
    drift_ratio = drift_res.get("ratio")
    drift_sample = drift_res.get("sample", 0)
    if drift_ratio is None:
        drift_verdict = (
            f"insufficient paired observations ({asset_type}: "
            f"{drift_sample} of {MIN_PAIRED_OBSERVATIONS} needed)"
        )
    elif drift_ratio >= REVENGE_SIZING_RATIO:
        drift_verdict = (
            f"revenge sizing signature in {asset_type}: sizing up by {drift_ratio:.2f}x after "
            f"losses (${drift_res['after_loss']:,.0f} vs ${drift_res['after_win']:,.0f} median, "
            f"N={drift_sample})"
        )
    elif drift_ratio <= 0.90:
        drift_verdict = (
            f"disciplined {asset_type} sizing: sizing down by {drift_ratio:.2f}x after losses "
            f"(N={drift_sample})"
        )
    else:
        drift_verdict = (
            f"stable {asset_type} sizing across wins and losses ({drift_ratio:.2f}x, "
            f"N={drift_sample})"
        )

    # Post-loss tempo
    buys = [f for f in asset_fills if f.side == "buy"]
    n_buys = len(buys)
    loss_exits = [t.exit_ts for t in asset_trips if t.pnl < 0]
    n_loss_exits = len(loss_exits)

    pace_ratio = None
    pace_sample = n_loss_exits
    if n_buys < MIN_TRIPS_FOR_BEHAVIOR or n_loss_exits < MIN_PAIRED_OBSERVATIONS:
        pace_verdict = (
            f"insufficient loss observations ({asset_type}: {n_loss_exits} of "
            f"{MIN_PAIRED_OBSERVATIONS} needed, {n_buys} total buys)"
        )
    else:
        span_days = max((buys[-1].ts - buys[0].ts).total_seconds() / 86400.0, 1.0)
        baseline_rate = n_buys / span_days

        window = timedelta(hours=REACTION_WINDOW_HOURS)
        spans = sorted((ts, ts + window) for ts in loss_exits)
        merged: list[list[datetime]] = []
        for s, e in spans:
            if merged and s <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], e)
            else:
                merged.append([s, e])

        covered_days = sum((e - s).total_seconds() for s, e in merged) / 86400.0
        in_window_buys = sum(1 for b in buys if any(s < b.ts <= e for s, e in merged))
        after_loss_rate = in_window_buys / covered_days if covered_days > 0 else 0.0

        if baseline_rate > 0:
            pace_ratio = round(after_loss_rate / baseline_rate, 4)
            if pace_ratio >= TILT_FREQUENCY_RATIO:
                pace_verdict = (
                    f"tilt tempo in {asset_type}: entering {pace_ratio:.2f}x faster in 24h after "
                    f"losses ({after_loss_rate:.2f} vs {baseline_rate:.2f} entries/day, "
                    f"N={pace_sample})"
                )
            elif pace_ratio <= 1.10:
                pace_verdict = (
                    f"disciplined {asset_type} tempo: post-loss pace matches baseline "
                    f"({pace_ratio:.2f}x, N={pace_sample})"
                )
            else:
                pace_verdict = (
                    f"mildly elevated {asset_type} pace ({pace_ratio:.2f}x, N={pace_sample})"
                )
        else:
            pace_verdict = f"baseline {asset_type} rate is zero"

    return AssetBehavior(
        asset_type=asset_type,
        sizing_drift_ratio=drift_ratio,
        sizing_drift_sample=drift_sample,
        sizing_drift_verdict=drift_verdict,
        post_loss_pace_ratio=pace_ratio,
        post_loss_pace_sample=pace_sample,
        post_loss_pace_verdict=pace_verdict,
    )


def analyze_autopsy(
    raw_fills: Sequence[Any],
    asof: date | None = None,
) -> TradingAutopsyReport:
    """Run full deterministic trading autopsy over fills (T103, D026).

    `asof` feeds the T108 expiry-aware matcher; None means the current UTC
    date. Tests pass it explicitly so the output is deterministic.
    """
    fills = [normalize_fill(f) for f in raw_fills]
    fills.sort(key=lambda f: f.ts)
    n_fills = len(fills)

    if n_fills == 0:
        empty_inst = InstrumentProfile(
            total_fills=0, option_fills=0, equity_fills=0, option_pct=0.0,
            dte0_fills=0, dte0_pct_of_options=None, calls_count=0, puts_count=0,
            total_notional=0.0, option_notional=0.0, equity_notional=0.0,
        )
        empty_perf = PerformanceSummary(
            round_trips=0, total_realized_pnl=0.0, wins=0, losses=0, scratches=0,
            win_rate=None, profit_factor=None, avg_win=None, avg_loss=None,
            payoff_ratio=None, largest_win=None, largest_loss=None,
            option_realized_pnl=0.0, equity_realized_pnl=0.0,
        )
        empty_asset_behav = AssetBehavior(
            asset_type="none", sizing_drift_ratio=None, sizing_drift_sample=0,
            sizing_drift_verdict="insufficient trades (0 fills)",
            post_loss_pace_ratio=None, post_loss_pace_sample=0,
            post_loss_pace_verdict="insufficient trades (0 fills)",
        )
        empty_behav = BehaviorSummary(
            options=empty_asset_behav,
            equities=empty_asset_behav,
            summary_verdict="insufficient trades (0 fills)",
        )
        return TradingAutopsyReport(
            total_fills=0,
            instrument_profile=empty_inst,
            performance=empty_perf,
            holding_periods=autopsy_holding_periods([]),
            behavior=empty_behav,
            day_of_week_distribution={},
            symbols=[],
            narrative=["No fills provided for autopsy analysis."],
            caveats=["Zero trading history to evaluate."],
        )

    # 1. Instrument Profile
    opt_fills = [f for f in fills if f.asset_type == "option"]
    eq_fills = [f for f in fills if f.asset_type != "option"]
    n_opt = len(opt_fills)
    n_eq = len(eq_fills)
    opt_pct = round(n_opt / n_fills, 4)

    dte0_fills = [f for f in opt_fills if f.is_0dte]
    n_dte0 = len(dte0_fills)
    dte0_pct = round(n_dte0 / n_opt, 4) if n_opt > 0 else None

    calls = [f for f in opt_fills if (f.option_right or "").lower() == "call"]
    puts = [f for f in opt_fills if (f.option_right or "").lower() == "put"]

    opt_notional = round(sum(f.notional for f in opt_fills), 2)
    eq_notional = round(sum(f.notional for f in eq_fills), 2)
    total_notional = round(opt_notional + eq_notional, 2)

    instrument_profile = InstrumentProfile(
        total_fills=n_fills,
        option_fills=n_opt,
        equity_fills=n_eq,
        option_pct=opt_pct,
        dte0_fills=n_dte0,
        dte0_pct_of_options=dte0_pct,
        calls_count=len(calls),
        puts_count=len(puts),
        total_notional=total_notional,
        option_notional=opt_notional,
        equity_notional=eq_notional,
    )

    # 2. FIFO Round Trips & Performance (T108: expiry-aware)
    trips = match_fifo_trips(fills, asof=asof)
    n_trips = len(trips)
    assumed = [t for t in trips if t.closed_by == "expiry_assumed"]
    n_assumed = len(assumed)
    assumed_pnl = round(sum(t.pnl for t in assumed), 2)

    wins = [t for t in trips if t.pnl > 0]
    losses = [t for t in trips if t.pnl < 0]
    scratches = [t for t in trips if t.pnl == 0]

    tot_pnl = round(sum(t.pnl for t in trips), 2)
    opt_pnl = round(sum(t.pnl for t in trips if t.asset_type == "option"), 2)
    eq_pnl = round(sum(t.pnl for t in trips if t.asset_type != "option"), 2)

    gross_win = sum(t.pnl for t in wins)
    gross_loss = abs(sum(t.pnl for t in losses))

    win_rate = round(len(wins) / n_trips, 4) if n_trips > 0 else None
    if gross_loss > 0:
        profit_factor = round(gross_win / gross_loss, 4)
    else:
        profit_factor = round(gross_win, 2) if gross_win > 0 else None

    avg_win = round(gross_win / len(wins), 2) if wins else None
    avg_loss = round(gross_loss / len(losses), 2) if losses else None
    if avg_win and avg_loss and avg_loss > 0:
        payoff_ratio = round(avg_win / avg_loss, 4)
    else:
        payoff_ratio = None

    largest_win = max((t.pnl for t in trips), default=None)
    largest_loss = min((t.pnl for t in trips), default=None)

    performance = PerformanceSummary(
        round_trips=n_trips,
        total_realized_pnl=tot_pnl,
        wins=len(wins),
        losses=len(losses),
        scratches=len(scratches),
        win_rate=win_rate,
        profit_factor=profit_factor,
        avg_win=avg_win,
        avg_loss=avg_loss,
        payoff_ratio=payoff_ratio,
        largest_win=largest_win,
        largest_loss=largest_loss,
        option_realized_pnl=opt_pnl,
        equity_realized_pnl=eq_pnl,
        expiry_assumed_count=n_assumed,
        expiry_assumed_pnl=assumed_pnl,
    )

    # 3. Holding Periods (T091b)
    holding_periods = autopsy_holding_periods(trips)

    # 4. Behavioral Tells (T069) — segregated by asset class
    opt_behavior = analyze_asset_behavior("option", trips, fills)
    eq_behavior = analyze_asset_behavior("equity", trips, fills)

    if opt_behavior.sizing_drift_ratio is not None and eq_behavior.sizing_drift_ratio is not None:
        summary_verdict = (
            f"{opt_behavior.sizing_drift_verdict} | {eq_behavior.sizing_drift_verdict}"
        )
    elif opt_behavior.sizing_drift_ratio is not None:
        summary_verdict = opt_behavior.sizing_drift_verdict
    elif eq_behavior.sizing_drift_ratio is not None:
        summary_verdict = eq_behavior.sizing_drift_verdict
    else:
        summary_verdict = (
            f"insufficient observations within asset classes "
            f"(options N={opt_behavior.sizing_drift_sample}, "
            f"equities N={eq_behavior.sizing_drift_sample}; {MIN_PAIRED_OBSERVATIONS} needed)"
        )

    behavior = BehaviorSummary(
        options=opt_behavior,
        equities=eq_behavior,
        summary_verdict=summary_verdict,
    )

    # 5. Day of Week Breakdown
    dow_table: dict[str, dict] = {d: {"fills": 0, "buys": 0, "sells": 0} for d in DAYS_OF_WEEK[:5]}
    for f in fills:
        day_name = DAYS_OF_WEEK[f.ts.weekday()]
        if day_name in dow_table:
            dow_table[day_name]["fills"] += 1
            if f.side == "buy":
                dow_table[day_name]["buys"] += 1
            else:
                dow_table[day_name]["sells"] += 1

    # 6. Per-Symbol Breakdown
    symbols_map: dict[str, dict] = {}
    for f in fills:
        s = symbols_map.setdefault(
            f.symbol,
            {
                "symbol": f.symbol,
                "fills": 0,
                "option_fills": 0,
                "equity_fills": 0,
                "dte0_fills": 0,
                "total_notional": 0.0,
                "realized_pnl": 0.0,
                "round_trips": 0,
                "wins": 0,
            },
        )
        s["fills"] += 1
        s["total_notional"] = round(s["total_notional"] + f.notional, 2)
        if f.asset_type == "option":
            s["option_fills"] += 1
            if f.is_0dte:
                s["dte0_fills"] += 1
        else:
            s["equity_fills"] += 1

    for t in trips:
        if t.symbol in symbols_map:
            s = symbols_map[t.symbol]
            s["round_trips"] += 1
            s["realized_pnl"] = round(s["realized_pnl"] + t.pnl, 2)
            if t.pnl > 0:
                s["wins"] += 1

    symbols_list = sorted(symbols_map.values(), key=lambda x: x["fills"], reverse=True)
    for s in symbols_list:
        s["win_rate"] = round(s["wins"] / s["round_trips"], 4) if s["round_trips"] > 0 else None

    # 7. Narrative Bullet Points (pure facts with N)
    narrative: list[str] = [
        f"Volume: {n_fills} executed fills (${total_notional:,.2f} total economic exposure).",
        (
            f"Asset Composition: {n_opt} options ({opt_pct:.1%}) and "
            f"{n_eq} equities ({1 - opt_pct:.1%})."
        ),
    ]
    if n_opt > 0:
        if dte0_pct is not None:
            dte0_str = f"{n_dte0} of {n_opt} option fills ({dte0_pct:.1%}) are 0DTE contracts."
        else:
            dte0_str = "0 0DTE fills."
        narrative.append(f"Options Horizon: {dte0_str} Calls: {len(calls)}, Puts: {len(puts)}.")

    if n_trips > 0:
        wr_str = f"{win_rate:.1%}" if win_rate is not None else "N/A"
        pf_str = f"{profit_factor:.2f}" if profit_factor is not None else "N/A"
        narrative.append(
            f"Performance: {n_trips} round trips, ${tot_pnl:,.2f} realized P&L "
            f"(Win rate: {wr_str} [{len(wins)}W/{len(losses)}L/{len(scratches)}S], PF: {pf_str})."
        )
        if n_assumed > 0:
            assumed_contracts = round(sum(t.qty for t in assumed), 2)
            narrative.append(
                f"Expired Positions (T108): {n_assumed} option lot(s) "
                f"({assumed_contracts:g} contracts) reached expiry with no recorded sale — "
                f"counted as total losses of ${assumed_pnl:,.2f} at exit 0 "
                f"(closed_by=expiry_assumed). Before this correction these losses were "
                f"invisible and every win rate was overstated (I026)."
            )
        if holding_periods["all_same_day_unrecorded"]:
            cnt = holding_periods["same_day_unrecorded_count"]
            narrative.append(
                f"Holding Time: All {cnt} closed round trips are same-day trades "
                f"(intraday duration within session is unrecorded on trade confirmations)."
            )
        elif holding_periods["has_unrecorded_intraday_times"]:
            cnt = holding_periods["same_day_unrecorded_count"]
            med = holding_periods["median_days"]
            med_s = f"{med:.1f} days" if med else "N/A"
            narrative.append(
                f"Holding Time: {cnt} same-day round trips (intraday times unrecorded); "
                f"multi-day median hold: {med_s}."
            )
        else:
            med_days = holding_periods.get("median_days")
            if med_days is not None:
                if med_days < 1.0:
                    hrs = med_days * 24.0
                    narrative.append(
                        f"Holding Time: Median hold is {hrs:.1f} hours ({med_days:.3f} days)."
                    )
                else:
                    narrative.append(f"Holding Time: Median hold is {med_days:.1f} calendar days.")
    else:
        narrative.append("Performance: No closed round trips detected in the provided fill window.")

    if opt_behavior.sizing_drift_ratio is not None:
        narrative.append(f"Options Sizing Behavior: {opt_behavior.sizing_drift_verdict}.")
    if eq_behavior.sizing_drift_ratio is not None:
        narrative.append(f"Equities Sizing Behavior: {eq_behavior.sizing_drift_verdict}.")
    if opt_behavior.sizing_drift_ratio is None and eq_behavior.sizing_drift_ratio is None:
        narrative.append(f"Sizing Behavior: {summary_verdict}.")

    caveats = [
        f"All metrics derived from {n_fills} fills. Small sample sizes are explicitly declared.",
        "Options notional includes the 100x contract multiplier.",
        "Trade confirmations lack intraday timestamps — same-day durations are marked unrecorded.",
        (
            "Behavioral sizing drift is computed strictly within asset classes "
            "(never mixing options with equities)."
        ),
    ]
    if n_assumed > 0:
        caveats.append(
            f"{n_assumed} round trip(s) are closed by ASSUMED worthless expiry, not an "
            "observed sale (T108). Exit 0 is wrong for any lot that was exercised or "
            "assigned — run scripts/reconcile_expiry.py against the monthly statements "
            "to confirm each one."
        )
    if win_rate == 1.0 and n_trips >= 5:
        # The owner's record proved a perfect win rate was a measurement gap, not
        # skill: expired-worthless lots generate no sale and silently vanish (I026).
        caveats.append(
            f"A 100% win rate across {n_trips} round trips is a BUG SIGNAL, not a result: "
            "the most common cause is invisible losses (e.g. options that expired "
            "worthless with no sale on record, I026). Verify data completeness before "
            "trusting any figure here."
        )

    return TradingAutopsyReport(
        total_fills=n_fills,
        instrument_profile=instrument_profile,
        performance=performance,
        holding_periods=holding_periods,
        behavior=behavior,
        day_of_week_distribution=dow_table,
        symbols=symbols_list,
        narrative=narrative,
        caveats=caveats,
    )
