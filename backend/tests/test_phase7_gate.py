"""T127 — the Phase 7 gate script: every check proven able to FAIL, then
shown green on a fully-prepared fixture. A gate that can't close is décor.

Loaded importlib-by-path (T113 precedent). The db fixture is the shared
in-memory session from test_paper_loop — no real database is touched.
"""

import importlib.util
from pathlib import Path

from research.custody import freeze_holdout, open_budget, record_attempt
from test_paper_loop import db  # noqa: F811,F401

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "phase7_gate.py"

spec = importlib.util.spec_from_file_location("phase7_gate_t127", SCRIPT)
assert spec is not None and spec.loader is not None
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

PREREG = ("# kronos-v1 pre-registration\n\n"
          "Contamination rule: Kronos trained through its cutoff, so only "
          "post-cutoff or paper-forward evaluation counts.\n"
          "Window: paper-forward 30 sessions. Budget: 3 attempts.\n")


def _prepared(session, tmp_path, revision="kronos-v1"):
    """Everything the gate demands: frozen holdout, open budget, prereg doc."""
    freeze_holdout(session, "oos-2026h2", ["NVDA"], "2026-07-01", "2026-12-31")
    open_budget(session, revision, max_attempts=3)
    exp = tmp_path / "experiments"
    exp.mkdir()
    (exp / f"{revision}.md").write_text(PREREG, encoding="utf-8")
    return exp


def test_gate_opens_when_every_precondition_holds(db, tmp_path, capsys):  # noqa: F811
    exp = _prepared(db, tmp_path)
    code = gate.run_gate(db, "kronos-v1", exp)
    out = capsys.readouterr().out
    assert code == 0 and "PHASE 7 GATE: OPEN" in out
    # the custody check proved the seam REFUSES, not merely exists
    assert "REFUSED 'NVDA'" in out
    # the isolation check names both canary sides
    assert "stripped across the boundary" in out


def test_gate_closes_without_a_frozen_holdout(db, tmp_path, capsys):  # noqa: F811
    exp = tmp_path / "experiments"
    exp.mkdir()
    (exp / "kronos-v1.md").write_text(PREREG, encoding="utf-8")
    open_budget(db, "kronos-v1", max_attempts=3)
    code = gate.run_gate(db, "kronos-v1", exp)
    out = capsys.readouterr().out
    assert code == 1 and "no FROZEN holdout" in out


def test_gate_closes_without_a_budget(db, tmp_path, capsys):  # noqa: F811
    exp = _prepared(db, tmp_path, revision="other-rev")
    code = gate.run_gate(db, "kronos-v1", exp)  # budget exists for OTHER rev
    out = capsys.readouterr().out
    assert code == 1 and "no budget for revision 'kronos-v1'" in out


def test_gate_closes_on_exhausted_budget(db, tmp_path, capsys):  # noqa: F811
    exp = _prepared(db, tmp_path)
    for _ in range(3):
        record_attempt(db, "kronos-v1", outcome="failed")  # failures COUNT
    code = gate.run_gate(db, "kronos-v1", exp)
    out = capsys.readouterr().out
    assert code == 1 and "budget exhausted" in out


def test_gate_closes_without_preregistration_or_without_the_rule(
        db, tmp_path, capsys):  # noqa: F811
    exp = _prepared(db, tmp_path)
    (exp / "kronos-v1.md").unlink()
    assert gate.run_gate(db, "kronos-v1", exp) == 1
    assert "no pre-registration" in capsys.readouterr().out
    # present but silent on the rule = still closed
    (exp / "kronos-v1.md").write_text("we will try the model\n",
                                      encoding="utf-8")
    assert gate.run_gate(db, "kronos-v1", exp) == 1
    assert "contamination" in capsys.readouterr().out


def test_gate_closes_if_the_custody_seam_serves(db, tmp_path, capsys, monkeypatch):  # noqa: F811
    # sabotage the rail: assert_servable becomes a no-op — the gate must
    # notice that the refusal it depends on never came (D027 #5)
    exp = _prepared(db, tmp_path)
    monkeypatch.setattr(gate, "assert_servable", lambda s, sym: None)
    code = gate.run_gate(db, "kronos-v1", exp)
    out = capsys.readouterr().out
    assert code == 1 and "did not refuse" in out


def test_gate_closes_if_the_boundary_leaks(db, tmp_path, capsys, monkeypatch):  # noqa: F811
    # sabotage isolation: pretend the child saw the planted canary (weights
    # carry the +1000 marker) — the gate must call the leak by name
    from research.isolation import IsolationResult

    exp = _prepared(db, tmp_path)
    fake = IsolationResult(weights=[1100.0, 1100.5, 1101.0, 1101.5],
                           error=None, stray_stdout_bytes=0, duration_s=0.1)
    monkeypatch.setattr(gate, "run_isolated", lambda *a, **k: fake)
    code = gate.run_gate(db, "kronos-v1", exp)
    out = capsys.readouterr().out
    assert code == 1 and "LEAKED" in out


def test_main_refuses_missing_db(tmp_path, capsys):
    code = gate.main(["--revision", "kronos-v1",
                      "--db", str(tmp_path / "absent.sqlite3")])
    out = capsys.readouterr().out
    assert code == 2 and "NOT CONFIGURED" in out and "alembic" in out
