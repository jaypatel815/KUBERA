"""T110b — the isolation boundary must pass BOTH ticket-named tests:
execution parity (identical numbers) and the adversarial probe (credential/
repo/holdout reads come back empty, visibly)."""

import os

import pytest
from research.custody import CustodyError, freeze_holdout, unlock_holdout
from research.isolation import (
    IsolationResult,
    assert_servable,
    run_inprocess,
    run_isolated,
)
from test_paper_loop import db  # noqa: F401

from backtest.strategies import build_strategy

# Self-contained momentum(60) — the SAME math as backtest.strategies'
# template, rewritten without imports because the child has no repo on its
# path (that unreachability is itself under test below).
MOMENTUM_SRC = """
def momentum(closes):
    if len(closes) < 61:
        return 0.0
    return 1.0 if closes[-1] / closes[-61] - 1.0 > 0.0 else 0.0
"""

CLOSES = [100.0 + (i % 7) - (0.02 * i if i > 40 else 0) + (0.06 * i if i > 70 else 0)
          for i in range(120)]


# ------------------------------------------------------- execution parity


def test_parity_isolated_equals_inprocess_equals_template():
    """The three-way check: boundary == no-boundary == the real template."""
    iso = run_isolated(MOMENTUM_SRC, "momentum", CLOSES)
    assert iso.error is None and iso.weights is not None
    inproc = run_inprocess(MOMENTUM_SRC, "momentum", CLOSES)
    assert iso.weights == inproc                       # boundary changes nothing
    template = build_strategy("momentum")              # momentum(lookback=60)
    expected = [float(template(CLOSES[:i])) for i in range(1, len(CLOSES) + 1)]
    assert iso.weights == expected                     # and matches the engine's math
    assert any(w == 1.0 for w in iso.weights) and any(w == 0.0 for w in iso.weights)


# ------------------------------------------------------- adversarial probe


def test_adversary_sees_no_credentials(monkeypatch):
    """Plant fake secrets in the PARENT env; the child must count ZERO."""
    monkeypatch.setenv("ALPACA_API_KEY", "fake-key-should-be-invisible")
    monkeypatch.setenv("FMP_API_KEY", "fake")
    monkeypatch.setenv("EDGAR_CONTACT", "owner@example.com")
    monkeypatch.setenv("KUBERA_DATABASE_URL", "sqlite:///secret.db")
    spy = """
import os
def spy(closes):
    hits = [k for k in os.environ
            if any(s in k.upper() for s in ("KEY", "SECRET", "CONTACT", "KUBERA", "ALPACA", "FMP"))]
    return float(len(hits))
"""
    r = run_isolated(spy, "spy", [1.0, 2.0])
    assert r.error is None
    assert r.weights == [0.0, 0.0]                     # empty-handed, as designed


def test_adversary_cannot_import_kubera_or_read_relative_env():
    """python -I + empty temp cwd: the repo is unreachable by import AND by
    relative path — the child doesn't know where it is."""
    probe = """
def probe(closes):
    score = 0.0
    try:
        import settings          # KUBERA's module — must not resolve
        score += 1.0
    except ImportError:
        pass
    try:
        import data.alpaca       # noqa
        score += 1.0
    except ImportError:
        pass
    try:
        open(".env")             # relative read in the empty temp cwd
        score += 1.0
    except OSError:
        pass
    return score
"""
    r = run_isolated(probe, "probe", [1.0])
    assert r.error is None and r.weights == [0.0]


def test_chatty_strategy_is_visible_but_cannot_corrupt_results():
    chatty = """
def chatty(closes):
    print("EXFIL:" + "x" * 50)
    return 0.5
"""
    r = run_isolated(chatty, "chatty", [1.0, 2.0])
    assert r.weights == [0.5, 0.5]                     # result channel intact
    assert r.stray_stdout_bytes >= 55 * 2              # the chatter is ON RECORD


def test_hang_is_killed_and_named():
    r = run_isolated("def hang(closes):\n while True: pass", "hang",
                     [1.0], timeout_s=2.0)
    assert r.weights is None
    assert r.error is not None and "timeout" in r.error
    assert r.duration_s < 30                           # actually killed


def test_child_exception_comes_back_named_not_silent():
    r = run_isolated("def boom(closes):\n raise ValueError('bad math')",
                     "boom", [1.0])
    assert r.weights is None
    assert r.error == "ValueError: bad math"
    assert isinstance(r, IsolationResult)


# --------------------------------------------------------- custody seam


def test_servable_refuses_guarded_allows_free_and_consumed(db):  # noqa: F811
    freeze_holdout(db, "oos-1", ["SPY"], "2026-01-01", "2026-06-30")
    with pytest.raises(CustodyError, match="holdout custody"):
        assert_servable(db, "spy")                     # case-insensitive refusal
    unlock_holdout(db, "oos-1", by="owner")
    with pytest.raises(CustodyError, match="holdout custody"):
        assert_servable(db, "SPY")                     # unlocked still guarded
    assert_servable(db, "NVDA")                        # un-guarded symbol serves


def test_parent_env_untouched_by_scrub():
    """The scrub builds a child env; it must never mutate the parent's."""
    before = dict(os.environ)
    run_isolated(MOMENTUM_SRC, "momentum", [1.0, 2.0])
    assert dict(os.environ) == before
