"""T110b — the isolation boundary for agent-written strategy code (D029).

This is the third Phase 7 precondition, split from T110a because it needed
real design, not a stub. The ticket demands the boundary pass BOTH:
  1. an EXECUTION-PARITY test — isolated and in-process runs produce
     identical numbers on identical inputs, or the sandbox silently changes
     results and every graded experiment is fiction;
  2. an ADVERSARIAL probe — strategy code that tries to read credentials or
     reach the repo must come back EMPTY-HANDED, with the attempt visible.

THREAT MODEL — stated honestly, because an overstated boundary is worse
than none: this protects against the research agent's code doing what D029
named — reading credentials from the environment, importing KUBERA's own
modules (settings, brokers, the DB), phoning results out through side
channels of the result payload, or consulting data it was not served. The
mechanism is a CHILD PROCESS with:
  - python -I (isolated mode: no PYTHONPATH, no user site, no script dir);
  - a SCRUBBED environment (allowlist of what an interpreter needs to boot,
    nothing else — no ALPACA_*, no FMP_*, no EDGAR_CONTACT, no KUBERA_*);
  - an EMPTY temp working directory (relative reads find nothing; the repo
    location is never disclosed via argv, cwd, or env);
  - data in through stdin ONLY (a JSON payload of closes), results out
    through a sentinel-tagged final line ONLY — anything else the code
    prints is counted and reported (a chatty strategy is visible, and it
    still cannot corrupt the result channel);
  - a hard timeout (a spinning strategy is killed and NAMED, not waited on).

NAMED LIMITATION: this is process isolation on the owner's own machine,
running as the owner's OS user. Code that already knows an absolute path
outside the temp dir can still read it — OS-level sandboxing (jails,
containers, seccomp) is explicitly out of scope for a personal research
loop and would be dishonest to claim from here. The adversarial tests
prove exactly what the design claims: env scrubbed, repo unreachable by
import or relative path, holdout refused at the data-serving seam.

The custody seam: Phase 7's data layer must call assert_servable() before
handing ANY bars to agent code — symbols under unconsumed holdout custody
(T110a's guarded_symbols) are refused BY NAME. Isolation without that
check would sandbox the code while feeding it the answer key.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass

from sqlalchemy.orm import Session

from research.custody import CustodyError, guarded_symbols

SENTINEL = "KUBERA_ISOLATION_RESULT:"

# What a Python interpreter needs to boot on the supported platforms and
# NOTHING else. Everything absent is the point: no keys, no contacts, no
# KUBERA_* configuration, no HOME (its dotfiles are a side channel).
_ENV_ALLOWLIST = ("PATH", "SYSTEMROOT", "SYSTEMDRIVE", "WINDIR", "COMSPEC",
                  "TEMP", "TMP", "LANG", "LC_ALL")

# The child bootstrap. Runs under `python -I` in an empty temp cwd. Reads
# {"source","func","closes"} from stdin, exec()s the strategy in a fresh
# namespace, calls it PROGRESSIVELY (closes[:1], closes[:2], …) exactly the
# way the backtest engine feeds strategies, and emits one sentinel line.
_BOOTSTRAP = r"""
import json, sys
payload = json.loads(sys.stdin.read())
out = {}
try:
    ns = {}
    exec(compile(payload["source"], "<strategy>", "exec"), ns)
    fn = ns[payload["func"]]
    closes = payload["closes"]
    out["weights"] = [float(fn(closes[:i])) for i in range(1, len(closes) + 1)]
except BaseException as e:  # noqa: BLE001 — the parent gets the NAME, always
    out["error"] = f"{type(e).__name__}: {e}"
print("KUBERA_ISOLATION_RESULT:" + json.dumps(out))
"""


@dataclass(frozen=True)
class IsolationResult:
    """What came back across the boundary — and what tried to."""

    weights: list[float] | None
    error: str | None            # named child failure (exception, timeout…)
    stray_stdout_bytes: int      # anything printed BESIDES the result line
    duration_s: float


def run_isolated(strategy_source: str, func_name: str,
                 closes: list[float], *, timeout_s: float = 10.0,
                 python: str | None = None) -> IsolationResult:
    """Execute self-contained strategy source across the boundary."""
    payload = json.dumps({"source": strategy_source, "func": func_name,
                          "closes": [float(c) for c in closes]})
    env = {k: os.environ[k] for k in _ENV_ALLOWLIST if k in os.environ}
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="kubera-iso-") as workdir:
        try:
            proc = subprocess.run(
                [python or sys.executable, "-I", "-c", _BOOTSTRAP],
                input=payload, capture_output=True, text=True,
                encoding="utf-8", errors="replace",
                env=env, cwd=workdir, timeout=timeout_s,
            )
        except subprocess.TimeoutExpired:
            return IsolationResult(
                weights=None,
                error=f"timeout: strategy exceeded {timeout_s}s and was "
                      "killed — a budget attempt, not a hang (D029)",
                stray_stdout_bytes=0,
                duration_s=time.monotonic() - started)
    duration = time.monotonic() - started

    result_line = None
    stray = 0
    for line in proc.stdout.splitlines():
        if line.startswith(SENTINEL):
            result_line = line[len(SENTINEL):]
        else:
            stray += len(line.encode("utf-8"))
    if result_line is None:
        return IsolationResult(
            weights=None,
            error=("child produced no result line (exit "
                   f"{proc.returncode}); stderr: {proc.stderr[:200]!r}"),
            stray_stdout_bytes=stray, duration_s=duration)
    try:
        out = json.loads(result_line)
    except ValueError:
        return IsolationResult(
            weights=None, error="result line was not valid JSON",
            stray_stdout_bytes=stray, duration_s=duration)
    return IsolationResult(
        weights=out.get("weights"), error=out.get("error"),
        stray_stdout_bytes=stray, duration_s=duration)


_BOOTSTRAP_JSON = r"""
import json, sys
payload = json.loads(sys.stdin.read())
out = {}
try:
    ns = {}
    exec(compile(payload["source"], "<research>", "exec"), ns)
    fn = ns[payload["func"]]
    result = fn(payload["payload"])
    if not isinstance(result, dict):
        raise TypeError(f"function returned {type(result).__name__}, expected dict")
    out["result"] = result
except BaseException as e:  # noqa: BLE001 — the parent gets the NAME, always
    out["error"] = f"{type(e).__name__}: {e}"
print("KUBERA_ISOLATION_RESULT:" + json.dumps(out))
"""


@dataclass(frozen=True)
class JsonCallResult:
    """One JSON-shaped call across the boundary (T122b) — same guarantees
    as IsolationResult, richer payload. The model-venv seam: `python=`
    points at an interpreter that HAS the research deps (torch, kronos);
    -I still scrubs PYTHONPATH/user-site, the env allowlist still strips
    keys, cwd is still an empty temp dir, the sentinel is still the only
    result channel."""

    result: dict | None
    error: str | None
    stray_stdout_bytes: int
    duration_s: float


def run_isolated_json(source: str, func_name: str, payload: dict, *,
                      timeout_s: float = 60.0,
                      python: str | None = None) -> JsonCallResult:
    """Execute self-contained source across the boundary, one call:
    func(payload_dict) -> dict. Everything non-JSON-serializable refuses
    in the CHILD with a named error — the parent never guesses."""
    body = json.dumps({"source": source, "func": func_name,
                       "payload": payload})
    env = {k: os.environ[k] for k in _ENV_ALLOWLIST if k in os.environ}
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="kubera-iso-") as workdir:
        try:
            proc = subprocess.run(
                [python or sys.executable, "-I", "-c", _BOOTSTRAP_JSON],
                input=body, capture_output=True, text=True,
                encoding="utf-8", errors="replace",
                env=env, cwd=workdir, timeout=timeout_s,
            )
        except subprocess.TimeoutExpired:
            return JsonCallResult(
                result=None,
                error=f"timeout: research call exceeded {timeout_s}s and "
                      "was killed — a budget attempt, not a hang (D029)",
                stray_stdout_bytes=0,
                duration_s=time.monotonic() - started)
    duration = time.monotonic() - started

    result_line, stray = None, 0
    for line in proc.stdout.splitlines():
        if line.startswith(SENTINEL):
            result_line = line[len(SENTINEL):]
        else:
            stray += len(line.encode("utf-8"))
    if result_line is None:
        return JsonCallResult(
            result=None,
            error=(f"child produced no result line (exit {proc.returncode}); "
                   f"stderr: {proc.stderr[:200]!r}"),
            stray_stdout_bytes=stray, duration_s=duration)
    try:
        out = json.loads(result_line)
    except ValueError:
        return JsonCallResult(result=None,
                              error="result line was not valid JSON",
                              stray_stdout_bytes=stray, duration_s=duration)
    return JsonCallResult(result=out.get("result"), error=out.get("error"),
                          stray_stdout_bytes=stray, duration_s=duration)


def run_inprocess(strategy_source: str, func_name: str,
                  closes: list[float]) -> list[float]:
    """The parity reference: same exec, same progressive feed, no boundary.
    TEST INSTRUMENT ONLY — production research code always crosses the
    boundary; this exists so the parity test has an honest yardstick."""
    ns: dict = {}
    exec(compile(strategy_source, "<strategy>", "exec"), ns)  # noqa: S102
    fn = ns[func_name]
    return [float(fn(closes[:i])) for i in range(1, len(closes) + 1)]


def assert_servable(session: Session, symbol: str) -> None:
    """The custody seam (T110a → T110b): refuse to serve data for symbols
    under UNCONSUMED holdout custody. Phase 7's data layer calls this before
    handing bars to agent code — isolation without it feeds the answer key."""
    symbol = symbol.upper()
    if symbol in guarded_symbols(session):
        raise CustodyError(
            f"'{symbol}' is under holdout custody (frozen or unlocked, not "
            "yet consumed) — the research boundary refuses to serve it; "
            "evaluate the holdout through custody, not around it (D029)")
