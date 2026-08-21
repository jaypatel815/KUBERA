"""T122b — the kronos-v1 experiment runner: paper-forward machinery only.

The pre-registration (docs/research/experiments/kronos-v1.md) is the
contract; this module is its mechanical enforcement:

- Forecasts are LOGGED AS MADE (ResearchForecast rows, made_at stamped,
  unique per (revision, symbol, date) — a re-forecast of the same session
  is refused by name). No scoring function reads the market until
  consumption: peeking mid-window is structurally impossible from here
  because scoring requires the custody consume, which works exactly once.
- The MODEL is an injection point: self-contained source + function name
  executed through the T110b boundary (`run_isolated_json`, optionally
  with a dedicated model-venv interpreter). This module never imports
  torch or Kronos — the sandbox that built it cannot, and that is the
  design: the same code runs the real model on the owner's machine by
  pointing --python at the venv that has it.
- AUTHORIZED CHANNEL, stated plainly: the custody seam (assert_servable)
  refuses holdout symbols to *general* research code. This runner is the
  REGISTERED experiment itself — its access to backward-looking closes
  for the guarded symbols is the authorized channel the pre-registration
  creates. It serves the model only closes STRICTLY BEFORE the forecast
  date (enforced here, tested), so the evaluation window's outcomes are
  never in any payload. The holdout row is not unlocked for this; the
  one-shot unlock+consume happens at scoring.
- SCORING runs once, at window end, against the frozen definition:
  interval coverage (realized return inside [p05, p95]) and the
  pre-committed toy rule (long when up_odds > 0.55, else flat, per
  symbol, equal-weight portfolio, costs charged on position CHANGES)
  versus buy-and-hold SPY. The verdict PASS/FAIL applies the two
  pre-stated criteria and nothing else; consume_holdout records it
  forever.

Every number here is deterministic given the logged rows and the realized
closes. FAIL is a real answer.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from data.models import HoldoutWindow, ResearchForecast
from research.custody import CustodyError, consume_holdout, params_hash
from research.isolation import JsonCallResult, run_isolated_json

UP_ODDS_LONG = 0.55          # pre-registered toy-rule threshold (kronos-v1.md)
COVERAGE_LO, COVERAGE_HI = 0.80, 0.97   # pre-registered calibration band
REQUIRED_KEYS = ("p05_frac", "p50_frac", "p95_frac", "up_odds")


class RunnerError(RuntimeError):
    """Named refusal — protocol violations are never silent."""


@dataclass(frozen=True)
class HoldoutDefinition:
    name: str
    symbols: list[str]
    start: str   # ISO
    end: str     # ISO
    frozen_hash: str


def load_definition(session: Session, name: str) -> HoldoutDefinition:
    import json as _json

    row = session.execute(
        select(HoldoutWindow).where(HoldoutWindow.name == name)
    ).scalars().first()
    if row is None:
        raise RunnerError(f"no holdout named '{name}' — freeze it first "
                          "(the gate would have said this too)")
    return HoldoutDefinition(
        name=row.name, symbols=_json.loads(row.symbols_json),
        start=row.start, end=row.end, frozen_hash=row.params_hash)


# ------------------------------------------------------------ forecasting


def call_model(model_source: str, func_name: str, symbol: str,
               closes: list[float], dates: list[str], forecast_date: str,
               *, python: str | None = None,
               timeout_s: float = 120.0,
               ohlcv: dict[str, list[float]] | None = None,
               config: dict[str, str] | None = None) -> dict:
    """One model call through the T110b boundary. Refuses, by name, any
    payload that would leak the forecast target: every supplied date must
    be STRICTLY BEFORE forecast_date. `ohlcv` carries the full bars the
    real Kronos needs (documented API: OHLCV DataFrame); `config` carries
    owner-machine strings like the Kronos repo path — passed per-call so
    no committed file ever holds a machine-local path."""
    if len(closes) != len(dates):
        raise RunnerError("closes and dates must align")
    if not closes:
        raise RunnerError(f"no history supplied for {symbol}")
    if max(str(d)[:10] for d in dates) >= forecast_date:
        raise RunnerError(
            f"history for {symbol} reaches {max(dates)} but the forecast "
            f"target is {forecast_date} — the model may only see strictly "
            "earlier sessions (paper-forward discipline)")
    if ohlcv is not None:
        bad = [k for k, v in ohlcv.items() if len(v) != len(dates)]
        if bad:
            raise RunnerError(
                f"ohlcv series {bad} misaligned with dates for {symbol} — "
                "a ragged payload silently shifts the model's view")
    res: JsonCallResult = run_isolated_json(
        model_source, func_name,
        {"symbol": symbol, "closes": [float(c) for c in closes],
         "dates": [str(d)[:10] for d in dates],
         "forecast_date": forecast_date,
         "ohlcv": ohlcv or {},
         "config": config or {}},
        python=python, timeout_s=timeout_s)
    if res.error is not None:
        raise RunnerError(f"model call failed for {symbol}: {res.error}")
    out = res.result or {}
    missing = [k for k in REQUIRED_KEYS if not isinstance(out.get(k),
                                                         (int, float))]
    if missing:
        raise RunnerError(
            f"model returned an incomplete forecast for {symbol}: missing "
            f"or non-numeric {missing} — refusing to log a partial row")
    if not out["p05_frac"] <= out["p50_frac"] <= out["p95_frac"]:
        raise RunnerError(
            f"model percentiles are not ordered for {symbol} "
            f"(p05={out['p05_frac']}, p50={out['p50_frac']}, "
            f"p95={out['p95_frac']}) — a malformed distribution is not "
            "data")
    if not 0.0 <= out["up_odds"] <= 1.0:
        raise RunnerError(f"up_odds {out['up_odds']} outside [0,1] for "
                          f"{symbol}")
    return {k: float(out[k]) for k in REQUIRED_KEYS}


def _validate_dist(symbol: str, out: dict) -> dict:
    missing = [k for k in REQUIRED_KEYS if not isinstance(out.get(k),
                                                         (int, float))]
    if missing:
        raise RunnerError(
            f"model returned an incomplete forecast for {symbol}: missing "
            f"or non-numeric {missing} — refusing to log a partial row")
    if not out["p05_frac"] <= out["p50_frac"] <= out["p95_frac"]:
        raise RunnerError(
            f"model percentiles are not ordered for {symbol} "
            f"(p05={out['p05_frac']}, p50={out['p50_frac']}, "
            f"p95={out['p95_frac']}) — a malformed distribution is not data")
    if not 0.0 <= out["up_odds"] <= 1.0:
        raise RunnerError(f"up_odds {out['up_odds']} outside [0,1] for "
                          f"{symbol}")
    return {k: float(out[k]) for k in REQUIRED_KEYS}


def call_model_batch(model_source: str, func_name: str,
                     series: dict[str, dict], forecast_date: str, *,
                     python: str | None = None,
                     timeout_s: float = 600.0,
                     config: dict[str, str] | None = None,
                     ) -> tuple[dict[str, dict], dict[str, str]]:
    """T140 — every symbol in ONE boundary call (one model load). `series`
    maps symbol -> {"closes", "dates", "ohlcv"}. The paper-forward check
    runs per symbol BEFORE anything crosses. Returns
    (validated_dists_by_symbol, named_errors_by_symbol) — a symbol's
    failure never poisons its neighbors; raises only when EVERY symbol
    failed or the call itself did."""
    for sym, s in series.items():
        if len(s["closes"]) != len(s["dates"]):
            raise RunnerError(f"closes and dates must align for {sym}")
        if not s["closes"]:
            raise RunnerError(f"no history supplied for {sym}")
        if max(str(d)[:10] for d in s["dates"]) >= forecast_date:
            raise RunnerError(
                f"history for {sym} reaches {max(s['dates'])} but the "
                f"forecast target is {forecast_date} — the model may only "
                "see strictly earlier sessions (paper-forward discipline)")
    res = run_isolated_json(
        model_source, func_name,
        {"forecast_date": forecast_date,
         "config": config or {},
         "series": {sym: {"closes": [float(c) for c in s["closes"]],
                          "dates": [str(d)[:10] for d in s["dates"]],
                          "ohlcv": s.get("ohlcv") or {}}
                    for sym, s in series.items()}},
        python=python, timeout_s=timeout_s)
    if res.error is not None:
        raise RunnerError(f"batch model call failed: {res.error}")
    raw = res.result or {}
    out: dict[str, dict] = {}
    errors: dict[str, str] = {}
    for sym in series:
        item = raw.get(sym)
        if not isinstance(item, dict):
            errors[sym] = "no result returned for this symbol"
        elif "error" in item:
            errors[sym] = str(item["error"])
        else:
            try:
                out[sym] = _validate_dist(sym, item)
            except RunnerError as e:
                errors[sym] = str(e)
    if errors and not out:
        raise RunnerError(f"every symbol failed: {errors}")
    return out, errors


def log_forecast(session: Session, revision: str, symbol: str,
                 forecast_date: str, basis_close: float,
                 dist: dict, source_note: str = "") -> ResearchForecast:
    """Append one forecast AS MADE. Duplicate (revision, symbol, date)
    refuses — re-forecasting a session after seeing more information is
    the exact temptation the unique constraint exists to stop."""
    row = ResearchForecast(
        revision=revision, symbol=symbol.upper(),
        forecast_date=forecast_date, basis_close=float(basis_close),
        p05_frac=dist["p05_frac"], p50_frac=dist["p50_frac"],
        p95_frac=dist["p95_frac"], up_odds=dist["up_odds"],
        source_note=source_note[:200])
    session.add(row)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise RunnerError(
            f"a forecast for {symbol.upper()} on {forecast_date} already "
            f"exists in revision '{revision}' — forecasts are made once, "
            "never revised (paper-forward discipline)")
    return row


def forecasts(session: Session, revision: str) -> list[ResearchForecast]:
    return list(session.execute(
        select(ResearchForecast)
        .where(ResearchForecast.revision == revision)
        .order_by(ResearchForecast.forecast_date, ResearchForecast.symbol)
    ).scalars().all())


# ------------------------------------------------------------ scoring (pure)


def coverage(rows: list[tuple[float, float, float]]) -> tuple[float | None, int]:
    """rows = (p05_frac, p95_frac, realized_frac). Fraction of realized
    moves inside the nominal 90% interval; None when there is nothing to
    score (never a fabricated 0.0)."""
    if not rows:
        return None, 0
    hit = sum(1 for lo, hi, r in rows if lo <= r <= hi)
    return hit / len(rows), len(rows)


def toy_rule_return(
    by_symbol: dict[str, list[tuple[float, float]]],
    cost_frac_per_change: float,
) -> float | None:
    """The pre-committed rule, exactly: per symbol, long (1.0) when
    up_odds > UP_ODDS_LONG else flat (0.0); portfolio return each day is
    the EQUAL-WEIGHT mean across symbols (flat legs contribute 0); costs
    charged on every position CHANGE at cost_frac_per_change (caller
    supplies the 2x-T090 number). Compounded. None when no days."""
    if not by_symbol:
        return None
    # each symbol carries an ordered list of (up_odds, realized_frac)
    n_days = {s: len(v) for s, v in by_symbol.items()}
    if len(set(n_days.values())) != 1:
        raise RunnerError(
            f"symbols have unequal day counts {n_days} — score only fully "
            "aligned windows; a partial symbol would silently reweight the "
            "portfolio")
    total = 1.0
    positions = {s: 0.0 for s in by_symbol}
    n = next(iter(n_days.values()))
    for i in range(n):
        day_ret = 0.0
        for s, pairs in by_symbol.items():
            up_odds, realized = pairs[i]
            target = 1.0 if up_odds > UP_ODDS_LONG else 0.0
            if target != positions[s]:
                day_ret -= cost_frac_per_change / len(by_symbol)
                positions[s] = target
            day_ret += (target * realized) / len(by_symbol)
        total *= (1.0 + day_ret)
    return total - 1.0


@dataclass(frozen=True)
class ScoreReport:
    revision: str
    holdout: str
    n_scored: int
    coverage_frac: float | None
    coverage_ok: bool
    toy_return: float | None
    benchmark_return: float | None
    toy_ok: bool
    verdict: str            # "PASS" | "FAIL" | "UNSCORABLE"
    notes: list[str]

    def summary(self) -> str:
        cov = f"{self.coverage_frac:.1%}" if self.coverage_frac is not None else "n/a"
        toy = f"{self.toy_return:+.2%}" if self.toy_return is not None else "n/a"
        bh = f"{self.benchmark_return:+.2%}" if self.benchmark_return is not None else "n/a"
        return (f"{self.verdict}: coverage {cov} (band "
                f"{COVERAGE_LO:.0%}-{COVERAGE_HI:.0%}), toy {toy} vs "
                f"b&h SPY {bh}, n={self.n_scored}")


def score(defn: HoldoutDefinition, rows: list[ResearchForecast],
          closes_by_symbol: dict[str, dict[str, float]],
          spy_closes: dict[str, float],
          cost_frac_per_change: float) -> ScoreReport:
    """Pure scorer: logged rows + realized closes -> verdict. Realized
    move for a forecast = close(forecast_date)/basis_close - 1, i.e. the
    model's own basis; a forecast whose session close is missing is
    NAMED and skipped, never guessed."""
    notes: list[str] = []
    in_window = [r for r in rows if defn.start <= r.forecast_date <= defn.end]
    if len(in_window) != len(rows):
        notes.append(f"{len(rows) - len(in_window)} forecast(s) outside "
                     "the frozen window ignored")
    cov_rows: list[tuple[float, float, float]] = []
    toy_pairs: dict[str, list[tuple[float, float]]] = {}
    skipped = 0
    for r in sorted(in_window, key=lambda x: (x.symbol, x.forecast_date)):
        px = closes_by_symbol.get(r.symbol, {}).get(r.forecast_date)
        if px is None or r.basis_close <= 0:
            skipped += 1
            continue
        realized = px / r.basis_close - 1.0
        cov_rows.append((r.p05_frac, r.p95_frac, realized))
        toy_pairs.setdefault(r.symbol, []).append((r.up_odds, realized))
    if skipped:
        notes.append(f"{skipped} forecast(s) skipped: no realized close "
                     "for that session (named, not guessed)")

    cov, n = coverage(cov_rows)
    try:
        toy = toy_rule_return(toy_pairs, cost_frac_per_change)
    except RunnerError as e:
        notes.append(str(e))
        toy = None

    bench = None
    window_days = sorted(d for d in spy_closes if defn.start <= d <= defn.end)
    if len(window_days) >= 2:
        bench = spy_closes[window_days[-1]] / spy_closes[window_days[0]] - 1.0
    else:
        notes.append("benchmark unscorable: fewer than 2 SPY closes in "
                     "the window")

    if cov is None or toy is None or bench is None:
        return ScoreReport(revision="", holdout=defn.name, n_scored=n,
                           coverage_frac=cov, coverage_ok=False,
                           toy_return=toy, benchmark_return=bench,
                           toy_ok=False, verdict="UNSCORABLE", notes=notes)
    cov_ok = COVERAGE_LO <= cov <= COVERAGE_HI
    toy_ok = toy >= bench
    verdict = "PASS" if (cov_ok and toy_ok) else "FAIL"
    return ScoreReport(revision="", holdout=defn.name, n_scored=n,
                       coverage_frac=cov, coverage_ok=cov_ok,
                       toy_return=toy, benchmark_return=bench,
                       toy_ok=toy_ok, verdict=verdict, notes=notes)


def consume_with_result(session: Session, defn: HoldoutDefinition,
                        report: ScoreReport) -> None:
    """The one-shot custody consumption: recomputes the params hash from
    the definition ACTUALLY scored, so a drifted definition refuses."""
    evaluated = params_hash(defn.symbols, defn.start, defn.end)
    try:
        consume_holdout(session, defn.name, report.summary(),
                        evaluated_hash=evaluated)
    except CustodyError as e:
        raise RunnerError(f"consumption refused: {e}")
