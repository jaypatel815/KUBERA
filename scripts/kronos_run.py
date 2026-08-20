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


def cmd_start(db: Path, another_attempt: bool = False) -> int:
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
        # The accidental-restart guard (observed live 2026-08-20: the owner
        # re-ran `start` minutes after attempt 1; only an argparse error
        # stopped attempt 2 being spent — luck is not a rail). A second
        # start with attempts already used must be EXPLICIT.
        import json as _json

        from sqlalchemy import select

        from data.models import ExperimentBudget

        row = s.execute(select(ExperimentBudget)
                        .where(ExperimentBudget.revision == REVISION)
                        ).scalars().first()
        used = len(_json.loads(row.attempts_json or "[]")) if row else 0
        if used > 0 and not another_attempt:
            print(f"REFUSED: attempt {used} is already recorded — the "
                  "campaign is ALREADY STARTED; re-running `start` would "
                  "spend another of your attempts for nothing. If you "
                  "truly mean to begin a NEW attempt (after a failed "
                  "campaign), run:  start --another-attempt")
            return 1
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
                 python: str | None, forecast_date: str | None,
                 model_config: dict[str, str] | None = None) -> int:
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
                    kept = [b for b in bars.bars
                            if str(b.date)[:10] < target]
                    if not kept:
                        raise RunnerError(f"no pre-{target} history")
                    dates = [str(b.date)[:10] for b in kept]
                    closes = [float(b.close) for b in kept]
                    # T122c: the real Kronos consumes OHLCV, not closes —
                    # the full bars ride the payload (same dates, aligned)
                    ohlcv = {
                        "open": [float(b.open) for b in kept],
                        "high": [float(b.high) for b in kept],
                        "low": [float(b.low) for b in kept],
                        "close": closes,
                        "volume": [float(b.volume) for b in kept],
                    }
                    dist = call_model(source, func, symbol, closes, dates,
                                      target, python=python,
                                      ohlcv=ohlcv, config=model_config)
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


def cmd_status(db: Path) -> int:
    """T133 — campaign status: COUNTS AND DATES ONLY. No realized prices,
    no coverage, no running score: a mid-window status that joined
    outcomes would be informal peeking, and the pre-registration says the
    one evaluation happens at consumption. What the owner can see is what
    the protocol has recorded, not how it is going."""
    import json as _json
    from datetime import date as _date

    from sqlalchemy import select

    from data.models import ExperimentBudget, HoldoutWindow

    engine, s = _session(db)
    try:
        hold = s.execute(select(HoldoutWindow)
                         .where(HoldoutWindow.name == HOLDOUT)
                         ).scalars().first()
        if hold is None:
            print(f"no holdout '{HOLDOUT}' — nothing registered yet")
            return 1
        budget = s.execute(select(ExperimentBudget)
                           .where(ExperimentBudget.revision == REVISION)
                           ).scalars().first()
        rows = forecasts(s, REVISION)
        print(f"campaign  : {REVISION} / holdout {hold.name} "
              f"[{hold.state}] hash {hold.params_hash}")
        print(f"window    : {hold.start} .. {hold.end}")
        today = _date.today().isoformat()
        if today < hold.start:
            print(f"            opens in "
                  f"{(_date.fromisoformat(hold.start) - _date.today()).days} "
                  "day(s)")
        elif today > hold.end:
            print("            window CLOSED — score --consume when ready")
        else:
            print(f"            {(_date.fromisoformat(hold.end) - _date.today()).days} "
                  "calendar day(s) remain")
        if budget is None:
            print("budget    : NOT OPENED — the gate would refuse `start`")
        else:
            used = len(_json.loads(budget.attempts_json or "[]"))
            print(f"budget    : {used}/{budget.max_attempts} attempts used "
                  "(failures count)")
        by_symbol: dict[str, int] = {}
        for r in rows:
            by_symbol[r.symbol] = by_symbol.get(r.symbol, 0) + 1
        days = sorted({r.forecast_date for r in rows})
        print(f"forecasts : {len(rows)} logged across {len(days)} "
              f"session(s)" + (f", latest {days[-1]}" if days else ""))
        for sym in sorted(by_symbol):
            print(f"            {sym}: {by_symbol[sym]}")
        print("(no outcomes shown mid-window BY DESIGN — the one "
              "evaluation happens at consumption, and not before)")
        return 0
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
    st = sub.add_parser("start")
    st.add_argument("--another-attempt", action="store_true",
                    help="explicitly spend a NEW attempt when one is "
                         "already recorded (after a failed campaign)")
    sub.add_parser("status")
    f = sub.add_parser("forecast")
    f.add_argument("--model-file", type=Path, required=True)
    f.add_argument("--func", default="forecast")
    f.add_argument("--python", default=None,
                   help="interpreter of the venv that has the model deps")
    f.add_argument("--date", default=None, help="session being forecast")
    f.add_argument("--model-config", action="append", default=[],
                   metavar="KEY=VALUE",
                   help="strings passed to the adapter (e.g. "
                        "kronos_repo=C:\\path\\to\\Kronos) — machine-local "
                        "paths live on the command line, never in a "
                        "committed file")
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
            return cmd_start(args.db, another_attempt=args.another_attempt)
        if args.cmd == "status":
            return cmd_status(args.db)
        if args.cmd == "forecast":
            cfg = {}
            for item in args.model_config:
                if "=" not in item:
                    print(f"REFUSED: --model-config '{item}' is not "
                          "KEY=VALUE")
                    return 1
                k, v = item.split("=", 1)
                cfg[k.strip()] = v.strip()
            return cmd_forecast(args.db, args.model_file, args.func,
                                args.python, args.date, model_config=cfg)
        return cmd_score(args.db, args.consume, args.cost_bps)
    except OperationalError as e:
        # the smoke run found this raw: name it instead (house rule)
        print(f"NOT CONFIGURED — a table is missing ({e.orig}); run "
              "`alembic -c backend/alembic.ini upgrade head` first")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
