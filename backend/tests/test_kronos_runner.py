"""T122b — the kronos-v1 runner: paper-forward discipline proven refusal by
refusal, the scorer hand-computed, consumption one-shot via real custody.

The model is ALWAYS a fake here (a source string through the real T110b
boundary) — the sandbox cannot run Kronos and must not pretend to. What
these tests pin is the MACHINERY the real model will ride.
"""

import pytest
from research.custody import freeze_holdout
from research.kronos_runner import (
    HoldoutDefinition,
    RunnerError,
    call_model,
    consume_with_result,
    coverage,
    forecasts,
    load_definition,
    log_forecast,
    score,
    toy_rule_return,
)
from test_paper_loop import db  # noqa: F811,F401

from data.models import HoldoutWindow

GOOD_MODEL = """
def forecast(payload):
    closes = payload["closes"]
    return {"p05_frac": -0.02, "p50_frac": 0.001, "p95_frac": 0.02,
            "up_odds": 0.6 if closes[-1] > closes[0] else 0.4}
"""

DIST = {"p05_frac": -0.02, "p50_frac": 0.001, "p95_frac": 0.02,
        "up_odds": 0.6}


def _defn(**over):
    base = dict(name="kronos-v1-fwd", symbols=["NVDA", "QQQ", "SPY"],
                start="2026-08-24", end="2026-10-02",
                frozen_hash="deadbeef00000000")
    base.update(over)
    return HoldoutDefinition(**base)


# --------------------------------------------------------------- model calls


def test_call_model_through_the_real_boundary():
    out = call_model(GOOD_MODEL, "forecast", "SPY",
                     [100.0, 101.0], ["2026-08-20", "2026-08-21"],
                     "2026-08-24", timeout_s=30.0)
    assert out == {"p05_frac": -0.02, "p50_frac": 0.001,
                   "p95_frac": 0.02, "up_odds": 0.6}


def test_call_model_refuses_history_reaching_the_target():
    # the paper-forward rule, enforced at the seam: history must be
    # STRICTLY before the forecast date
    with pytest.raises(RunnerError, match="strictly earlier"):
        call_model(GOOD_MODEL, "forecast", "SPY",
                   [100.0, 101.0], ["2026-08-21", "2026-08-24"],
                   "2026-08-24")


def test_call_model_refuses_malformed_distributions():
    bad_order = """
def forecast(payload):
    return {"p05_frac": 0.02, "p50_frac": 0.0, "p95_frac": -0.02,
            "up_odds": 0.5}
"""
    with pytest.raises(RunnerError, match="not ordered"):
        call_model(bad_order, "forecast", "SPY", [100.0], ["2026-08-20"],
                   "2026-08-24", timeout_s=30.0)
    partial = """
def forecast(payload):
    return {"p05_frac": -0.01, "up_odds": 0.5}
"""
    with pytest.raises(RunnerError, match="incomplete"):
        call_model(partial, "forecast", "SPY", [100.0], ["2026-08-20"],
                   "2026-08-24", timeout_s=30.0)


# ------------------------------------------------------------- forecast log


def test_log_forecast_once_never_revised(db):  # noqa: F811
    log_forecast(db, "kronos-v1", "spy", "2026-08-24", 100.0, DIST)
    rows = forecasts(db, "kronos-v1")
    assert len(rows) == 1 and rows[0].symbol == "SPY"
    assert rows[0].made_at is not None  # stamped AS MADE
    with pytest.raises(RunnerError, match="never\\s+revised"):
        log_forecast(db, "kronos-v1", "SPY", "2026-08-24", 101.0, DIST)


def test_load_definition_names_missing_holdout(db):  # noqa: F811
    with pytest.raises(RunnerError, match="no holdout named"):
        load_definition(db, "ghost")
    freeze_holdout(db, "kronos-v1-fwd", ["SPY", "QQQ", "NVDA"],
                   "2026-08-24", "2026-10-02")
    defn = load_definition(db, "kronos-v1-fwd")
    assert defn.symbols == ["NVDA", "QQQ", "SPY"]  # custody sorts+uppers


# ----------------------------------------------------------- scoring (hand)


def test_coverage_hand_computed():
    rows = [(-0.02, 0.02, 0.01),   # inside
            (-0.02, 0.02, 0.03),   # above
            (-0.02, 0.02, -0.02)]  # boundary counts as inside
    frac, n = coverage(rows)
    assert n == 3 and frac == pytest.approx(2 / 3)
    assert coverage([]) == (None, 0)  # nothing to score is None, never 0.0


def test_toy_rule_hand_computed_two_symbols_with_costs():
    # A: long both days (odds .6); B: flat then long (.4 -> .6)
    # cost 0.001 per change, split across 2 symbols in the day return
    by_symbol = {
        "A": [(0.6, 0.01), (0.6, 0.02)],
        "B": [(0.4, -0.05), (0.6, 0.01)],
    }
    # day1: A enters (-0.0005) + A ret 0.005 ; B flat -> 0.0045
    # day2: B enters (-0.0005) + A 0.01 + B 0.005 -> 0.0145
    expected = (1 + 0.0045) * (1 + 0.0145) - 1
    got = toy_rule_return(by_symbol, cost_frac_per_change=0.001)
    assert got == pytest.approx(expected, abs=1e-12)


def test_toy_rule_refuses_misaligned_symbols():
    with pytest.raises(RunnerError, match="unequal day counts"):
        toy_rule_return({"A": [(0.6, 0.01)],
                         "B": [(0.6, 0.01), (0.6, 0.01)]}, 0.0)


def _mk_row(session, symbol, day, basis, dist=DIST):
    return log_forecast(session, "kronos-v1", symbol, day, basis, dist)


def test_score_end_to_end_verdict_and_named_skips(db):  # noqa: F811
    defn = _defn(symbols=["SPY"])
    _mk_row(db, "SPY", "2026-08-24", 100.0)                 # realized +1%
    _mk_row(db, "SPY", "2026-08-25", 101.0)                 # no close -> skip
    _mk_row(db, "SPY", "2026-08-20", 99.0)                  # outside window
    rows = forecasts(db, "kronos-v1")
    closes = {"SPY": {"2026-08-24": 101.0, "2026-10-02": 102.0}}
    report = score(defn, rows, closes, spy_closes=closes["SPY"],
                   cost_frac_per_change=0.0)
    assert report.n_scored == 1
    assert report.coverage_frac == 1.0          # +1% inside [-2%, +2%]
    assert any("outside the frozen window" in n for n in report.notes)
    assert any("skipped" in n for n in report.notes)
    # coverage 100% is ABOVE the honest band (uselessly wide) -> FAIL
    assert report.coverage_ok is False and report.verdict == "FAIL"
    # toy: long day1 at +1% vs b&h 101->102... benchmark spans the window
    assert report.benchmark_return == pytest.approx(102.0 / 101.0 - 1)


def test_score_unscorable_never_consumes_shape(db):  # noqa: F811
    defn = _defn(symbols=["SPY"])
    _mk_row(db, "SPY", "2026-08-24", 100.0)
    rows = forecasts(db, "kronos-v1")
    report = score(defn, rows, {"SPY": {}}, spy_closes={},
                   cost_frac_per_change=0.0)
    assert report.verdict == "UNSCORABLE"
    assert any("benchmark unscorable" in n for n in report.notes)


# ------------------------------------------------------------- consumption


def test_consume_records_once_and_refuses_twice(db):  # noqa: F811
    freeze_holdout(db, "kronos-v1-fwd", ["SPY"], "2026-08-24", "2026-10-02")
    from research.custody import unlock_holdout
    unlock_holdout(db, "kronos-v1-fwd", by="owner")
    defn = load_definition(db, "kronos-v1-fwd")
    _mk_row(db, "SPY", "2026-08-24", 100.0)
    closes = {"SPY": {"2026-08-24": 101.0, "2026-10-02": 102.0}}
    report = score(defn, forecasts(db, "kronos-v1"), closes,
                   closes["SPY"], 0.0)
    consume_with_result(db, defn, report)
    row = db.query(HoldoutWindow).filter_by(name="kronos-v1-fwd").one()
    assert row.state == "consumed" and "FAIL" in (row.result_summary or "")
    with pytest.raises(RunnerError, match="consumption refused"):
        consume_with_result(db, defn, report)  # the one shot is spent


# --- T122c: the payload extension (ohlcv + config across the boundary) -------


def test_call_model_delivers_ohlcv_and_config_to_the_child():
    echo = """
def forecast(payload):
    o = payload["ohlcv"]
    cfg = payload["config"]
    # encode what the child SAW into the returned floats (bounded fields)
    return {"p05_frac": -abs(float(o["high"][0]) / 1e6),
            "p50_frac": 0.0,
            "p95_frac": float(len(cfg)) / 100.0,
            "up_odds": 1.0 if cfg.get("kronos_repo") == "/tmp/kr" else 0.0}
"""
    out = call_model(
        echo, "forecast", "SPY", [100.0], ["2026-08-20"], "2026-08-24",
        timeout_s=30.0,
        ohlcv={"open": [99.8], "high": [100.5], "low": [99.4],
               "close": [100.0], "volume": [1e6]},
        config={"kronos_repo": "/tmp/kr"})
    assert out["up_odds"] == 1.0          # config crossed the boundary
    assert out["p05_frac"] == pytest.approx(-100.5 / 1e6)  # ohlcv did too
    assert out["p95_frac"] == pytest.approx(0.01)


def test_call_model_refuses_misaligned_ohlcv():
    with pytest.raises(RunnerError, match="misaligned"):
        call_model(GOOD_MODEL, "forecast", "SPY", [100.0, 101.0],
                   ["2026-08-19", "2026-08-20"], "2026-08-24",
                   ohlcv={"open": [99.0]})  # 1 vs 2 dates


def test_committed_adapter_is_readable_and_carries_no_machine_paths():
    # the T122b objection made reviewability the control: pin size and
    # cleanliness of the committed adapter + shape check
    from pathlib import Path
    root = Path(__file__).resolve().parents[2] / "scripts"
    for name in ("kronos_adapter.py", "kronos_shape_check.py"):
        text = (root / name).read_text(encoding="utf-8")
        assert "C:\\Users" not in text and "/home/" not in text
        assert len(text.splitlines()) < 140, f"{name} outgrew reviewability"
    adapter = (root / "kronos_adapter.py").read_text(encoding="utf-8")
    # the distribution is drawn, never averaged (sample_count stays 1)
    assert "sample_count=1" in adapter and "N_PATHS" in adapter
    assert "config" in adapter and "kronos_repo" in adapter


# --- T133: campaign status — counts and dates only, never outcomes -----------


def test_cli_status_shows_counts_never_outcomes(tmp_path, capsys):
    import importlib.util
    from pathlib import Path as _P

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from data.models import Base

    dbfile = tmp_path / "kubera.sqlite3"
    engine = create_engine(f"sqlite:///{dbfile.as_posix()}")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as s:
        freeze_holdout(s, "kronos-v1-fwd", ["SPY", "QQQ"],
                       "2026-08-24", "2026-10-02")
        from research.custody import open_budget, record_attempt
        open_budget(s, "kronos-v1", max_attempts=3)
        record_attempt(s, "kronos-v1", outcome="started")
        log_forecast(s, "kronos-v1", "SPY", "2026-08-24", 100.0, DIST)
        log_forecast(s, "kronos-v1", "QQQ", "2026-08-24", 200.0, DIST)
        log_forecast(s, "kronos-v1", "SPY", "2026-08-25", 101.0, DIST)
    engine.dispose()

    script = _P(__file__).resolve().parents[2] / "scripts" / "kronos_run.py"
    spec = importlib.util.spec_from_file_location("kronos_run_t133", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.cmd_status(dbfile) == 0
    out = capsys.readouterr().out
    assert "1/3 attempts used" in out
    assert "3 logged across 2 session(s), latest 2026-08-25" in out
    assert "SPY: 2" in out and "QQQ: 1" in out
    assert "BY DESIGN" in out
    # the anti-peek pin: no price, return, or coverage figure appears
    for banned in ("coverage", "%", "101", "200.0"):
        assert banned not in out


# --- accidental-restart guard (observed live 2026-08-20) ---------------------


def test_start_refuses_restart_without_explicit_flag(tmp_path, capsys,
                                                     monkeypatch):
    """The owner re-ran `start` minutes after attempt 1; only an argparse
    error stopped attempt 2 being spent. Now the guard refuses — and
    proves it spent NOTHING — unless --another-attempt is explicit."""
    import importlib.util
    from pathlib import Path as _P
    from types import SimpleNamespace

    from research.custody import open_budget, record_attempt
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from data.models import Base

    dbfile = tmp_path / "kubera.sqlite3"
    engine = create_engine(f"sqlite:///{dbfile.as_posix()}")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as s:
        freeze_holdout(s, "kronos-v1-fwd", ["SPY"],
                       "2026-08-24", "2026-10-02")
        open_budget(s, "kronos-v1", max_attempts=3)
        record_attempt(s, "kronos-v1", outcome="started")  # attempt 1 spent
    engine.dispose()

    script = _P(__file__).resolve().parents[2] / "scripts" / "kronos_run.py"
    spec = importlib.util.spec_from_file_location("kronos_run_guard", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # the gate subprocess is not under test here — pretend it printed OPEN
    monkeypatch.setattr(mod.subprocess, "run",
                        lambda *a, **k: SimpleNamespace(returncode=0,
                                                        stdout="", stderr=""))

    assert mod.cmd_start(dbfile) == 1
    out = capsys.readouterr().out
    assert "ALREADY STARTED" in out and "--another-attempt" in out
    assert mod.cmd_status(dbfile) == 0
    assert "1/3 attempts used" in capsys.readouterr().out  # NOTHING spent

    # the explicit flag is the legitimate path: attempt 2 records
    assert mod.cmd_start(dbfile, another_attempt=True) == 0
    assert "ATTEMPT 2 recorded" in capsys.readouterr().out


# --- T140: one boundary call, one model load, per-symbol isolation -----------

BATCH_MODEL = """
def forecast_batch(payload):
    out = {}
    for sym, s in payload["series"].items():
        if sym == "BAD":
            out[sym] = {"error": "synthetic per-symbol failure"}
        else:
            out[sym] = {"p05_frac": -0.02, "p50_frac": 0.0,
                        "p95_frac": 0.02,
                        "up_odds": 0.6 if s["ohlcv"] else 0.4}
    return out
"""


def _series(sym="SPY"):
    return {"closes": [100.0, 101.0], "dates": ["2026-08-19", "2026-08-20"],
            "ohlcv": {"open": [99.8, 100.5], "high": [100.2, 101.3],
                      "low": [99.5, 100.1], "close": [100.0, 101.0],
                      "volume": [1e6, 1.1e6]}}


def test_batch_call_isolates_per_symbol_failures():
    from research.kronos_runner import call_model_batch

    dists, errors = call_model_batch(
        BATCH_MODEL, "forecast_batch",
        {"SPY": _series(), "BAD": _series(), "QQQ": _series()},
        "2026-08-24", timeout_s=30.0)
    assert set(dists) == {"SPY", "QQQ"}
    assert dists["SPY"]["up_odds"] == 0.6     # ohlcv reached the child
    assert errors == {"BAD": "synthetic per-symbol failure"}


def test_batch_call_paper_forward_checked_before_crossing():
    from research.kronos_runner import call_model_batch

    leaky = _series()
    leaky["dates"] = ["2026-08-20", "2026-08-24"]  # reaches the target
    with pytest.raises(RunnerError, match="strictly earlier"):
        call_model_batch(BATCH_MODEL, "forecast_batch",
                         {"SPY": leaky}, "2026-08-24")


def test_batch_call_raises_when_every_symbol_fails():
    from research.kronos_runner import call_model_batch

    with pytest.raises(RunnerError, match="every symbol failed"):
        call_model_batch(BATCH_MODEL, "forecast_batch",
                         {"BAD": _series()}, "2026-08-24", timeout_s=30.0)


def test_committed_adapter_has_the_batch_entry_and_one_load():
    from pathlib import Path
    text = (Path(__file__).resolve().parents[2] / "scripts" /
            "kronos_adapter.py").read_text(encoding="utf-8")
    assert "def forecast_batch(" in text and "def forecast(" in text
    # ONE load for the batch: _predictor called once in forecast_batch
    batch_body = text.split("def forecast_batch(")[1]
    assert batch_body.count("_predictor(") == 1
    # the equal-length predict_batch constraint is refused BY NAME
    assert "predict_batch is deliberately NOT used" in text
