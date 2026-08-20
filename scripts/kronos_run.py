"""T122b — the kronos-v1 campaign CLI. Owner usage, in protocol order:

    py scripts\\kronos_run.py start
        Runs the Phase 7 gate; if OPEN, records ONE budget attempt
        ("started" — an aborted campaign still spent it, failures count).

    py scripts\\kronos_run.py forecast --model-file path\\to\\kronos_adapter.py
        [--func forecast] [--python C:\\path\\to\\model-venv\\python.exe]
        [--date YYYY-MM-DD]
        Logs today's forecasts for every holdout symbol, AS MADE. The
        model file must define  forecast(payload: dict) -> dict  with
        keys p05_frac/p50_frac/p95_frac/up_odds; it executes across the
        T110b boundary (scrubbed env, temp cwd, sentinel channel) using
        --python's interpreter, which is where torch/Kronos live. There
        is deliberately NO built-in model: a stub forecasting in
        production would be fabricated data (AGENTS.md priority 1).

    py scripts\\kronos_run.py score [--consume] [--cost-bps N]
        At window end: coverage + toy-rule-vs-b&h against the frozen
        definition. --consume records the verdict through custody's
        one-shot consumption. Costs default to 2x the live T090
        estimated half-spread across the holdout symbols; --cost-bps
        overrides (already-doubled value) for reproducibility.

Exit codes: 0 ok, 1 refusal/failure (named), 2 not configured.
"""

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from research.custody import CustodyError, record_attempt  # noqa: E402
from research.kronos_runner import (  # noqa: E402
    RunnerError,
    call_model,
    consume_with_result,
    forecasts,
    load_definition,
    log_forecast,
    score,
)
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from analysis.market_time import market_today  # noqa: E402
from data.market_data import MarketDataClient, MarketDataError  # noqa: E402
from settings import ConfigError  # noqa: E402

REVISION = "kronos-v1"
HOLDOUT = "kronos-v1-fwd"
DEFAULT_DB = REPO_ROOT / "kubera.sqlite3"


def _session(db: Path):
    engine = create_engine(f"sqlite:///{db.as_posix()}")
    return engine, sessionmaker(bind=engine)()


def cmd_start(db: Path) -> int:
    gate = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "phase7_gate.py"),
         "--revision", REVISION, "--db", str(db)],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(gate.stdout, end="")
    if gate.returncode != 0:
        print("REFUSED: the gate is not OPEN — fix its named reasons; "
              "starting anyway is the move the gate exists to stop")
        return 1
    engine, s = _session(db)
    try:
        receipt = record_attempt(s, REVISION, outcome="started",
                                 note="campaign start via kronos_run.py")
        print(f"ATTEMPT {receipt.attempt_number} recorded "
              f"({receipt.remaining} remaining — failures count). The "
              "window runs per the pre-registration; forecast each "
              "session, score ONCE at the end.")
        return 0
    except CustodyError as e:
        print(f"REFUSED: {e}")
        return 1
    finally:
        s.close()
        engine.dispose()


def cmd_forecast(db: Path, model_file: Path, func: str,
                 python: str | None, forecast_date: str | None) -> int:
    if not model_file.exists():
        print(f"REFUSED: model file {model_file} does not exist — there is "
              "no built-in model on purpose (a stub forecast would be "
              "fabricated data)")
        return 1
    source = model_file.read_text(encoding="utf-8")
    target = forecast_date or market_today().isoformat()
    engine, s = _session(db)
    try:
        defn = load_definition(s, HOLDOUT)
        if not (defn.start <= target <= defn.end):
            print(f"REFUSED: {target} is outside the frozen window "
                  f"{defn.start}..{defn.end} — forecasts outside it would "
                  "never be scored and only muddy the record")
            return 1
        try:
            market = MarketDataClient()
        except ConfigError as e:
            print(f"NOT CONFIGURED: {e}")
            return 2
        failures = 0
        with market:
            for symbol in defn.symbols:
                try:
                    bars = market.get_daily_bars(symbol, days=500)
                    hist = [(str(b.date)[:10], float(b.close))
                            for b in bars.bars if str(b.date)[:10] < target]
                    if not hist:
                        raise RunnerError(f"no pre-{target} history")
                    dates = [d for d, _ in hist]
                    closes = [c for _, c in hist]
                    dist = call_model(source, func, symbol, closes, dates,
                                      target, python=python)
                    row = log_forecast(
                        s, REVISION, symbol, target, closes[-1], dist,
                        source_note=f"model={model_file.name}")
                    print(f"{symbol} {target}: logged as made at "
                          f"{row.made_at.isoformat()} — p05 "
                          f"{dist['p05_frac']:+.2%} .. p95 "
                          f"{dist['p95_frac']:+.2%}, up-odds "
                          f"{dist['up_odds']:.0%} (internal signal, "
                          "D035 — never narrated as a point call)")
                except (RunnerError, MarketDataError) as e:
                    failures += 1
                    print(f"{symbol} {target}: FAILED — {e}")
        return 1 if failures else 0
    finally:
        s.close()
        engine.dispose()


def _twice_t090_cost_frac(market: MarketDataClient,
                          symbols: list[str]) -> float:
    """2x the mean T090 estimated per-side cost across the holdout
    symbols, as a fraction. Named refusal if no quote answers."""
    from analysis.liquidity import estimated_cost_bps, spread_bps

    costs = []
    for sym in symbols:
        q = market.get_latest_quote(sym)
        costs.append(estimated_cost_bps(spread_bps(q.bid, q.ask)))
    if not costs:
        raise RunnerError("no quotes answered — pass --cost-bps explicitly")
    return 2.0 * (sum(costs) / len(costs)) / 10_000.0


def cmd_score(db: Path, consume: bool, cost_bps: float | None) -> int:
    engine, s = _session(db)
    try:
        defn = load_definition(s, HOLDOUT)
        rows = forecasts(s, REVISION)
        if not rows:
            print("REFUSED: no forecasts logged — there is nothing to "
                  "score, and consuming the holdout on nothing would waste "
                  "its one shot")
            return 1
        try:
            market = MarketDataClient()
        except ConfigError as e:
            print(f"NOT CONFIGURED: {e}")
            return 2
        with market:
            closes_by_symbol: dict[str, dict[str, float]] = {}
            for sym in set(defn.symbols) | {"SPY"}:
                bars = market.get_daily_bars(sym, days=250)
                closes_by_symbol[sym] = {str(b.date)[:10]: float(b.close)
                                         for b in bars.bars}
            if cost_bps is not None:
                cost_frac = cost_bps / 10_000.0
            else:
                cost_frac = _twice_t090_cost_frac(market, defn.symbols)
        report = score(defn, rows, closes_by_symbol,
                       closes_by_symbol["SPY"], cost_frac)
        print(report.summary())
        for note in report.notes:
            print(f"  note: {note}")
        print(f"  cost per position change: {cost_frac:.4%} "
              f"({'--cost-bps override' if cost_bps is not None else '2x live T090 estimate'})")
        if report.verdict == "UNSCORABLE":
            print("not consuming: an unscorable window keeps its one shot")
            return 1
        if consume:
            consume_with_result(s, defn, report)
            print(f"HOLDOUT CONSUMED — the verdict is on the record "
                  f"forever: {report.verdict}. A FAIL is a real answer "
                  "(D037: that is the base rate; we measured ours).")
        else:
            print("(dry read — pass --consume to record the one "
                  "evaluation; do that ONCE, at window end)")
        return 0
    except (RunnerError, MarketDataError) as e:
        print(f"FAILED: {e}")
        return 1
    finally:
        s.close()
        engine.dispose()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="kronos-v1 campaign runner (T122b) — paper-forward only.")
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("start")
    f = sub.add_parser("forecast")
    f.add_argument("--model-file", type=Path, required=True)
    f.add_argument("--func", default="forecast")
    f.add_argument("--python", default=None,
                   help="interpreter of the venv that has the model deps")
    f.add_argument("--date", default=None, help="session being forecast")
    sc = sub.add_parser("score")
    sc.add_argument("--consume", action="store_true")
    sc.add_argument("--cost-bps", type=float, default=None,
                    help="already-doubled per-change cost override")
    args = ap.parse_args(argv)

    if not args.db.exists():
        print(f"NOT CONFIGURED — no database at {args.db}")
        return 2
    try:
        if args.cmd == "start":
            return cmd_start(args.db)
        if args.cmd == "forecast":
            return cmd_forecast(args.db, args.model_file, args.func,
                                args.python, args.date)
        return cmd_score(args.db, args.consume, args.cost_bps)
    except OperationalError as e:
        # the smoke run found this raw: name it instead (house rule)
        print(f"NOT CONFIGURED — a table is missing ({e.orig}); run "
              "`alembic -c backend/alembic.ini upgrade head` first")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
