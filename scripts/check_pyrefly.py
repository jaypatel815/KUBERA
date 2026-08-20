"""T125 — the type gate: pyrefly must report EXACTLY ZERO errors.

I023's arc, mechanized: T101 drove the checker to zero; T045 broke the
invariant the very next ticket and the count sat wrong for days because
zero was a HABIT, not a gate. Then 2026-08-20 made it a true zero again
(cast on the one expressibility gap) — this step keeps it true by force.
The checker caught four real bugs before they shipped (a crash-on-first-
run signature, a None-typed gap, two unbound names); every error it
reports gets INVESTIGATED, never suppressed (pyrefly.toml has the rules).

Robustness: pyrefly's exit code is not documented as a stable contract,
so this wrapper checks BOTH the return code and the parsed
"INFO N error(s)" line — a format drift fails LOUD (unparseable output
is a failure, not a pass).
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    proc = subprocess.run(
        [sys.executable, "-m", "pyrefly", "check"],
        cwd=ROOT / "backend", capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    text = (proc.stdout or "") + (proc.stderr or "")
    m = re.search(r"INFO (\d[\d,]*) errors?", text)
    if m is None:
        print(text[-2000:])
        print("pyrefly: could not parse the error-count line — format "
              "drift; treating as FAILURE (a gate that can't read its "
              "instrument is not a gate)")
        return 1
    count = int(m.group(1).replace(",", ""))
    if count == 0 and proc.returncode == 0:
        print("pyrefly: 0 errors — the canary is exactly zero (I023)")
        return 0
    print(text[-4000:])
    print(f"pyrefly: {count} error(s), exit {proc.returncode} — the canary "
          "is EXACTLY ZERO; investigate before suppressing (pyrefly.toml)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
