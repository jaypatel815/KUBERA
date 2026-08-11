# ISSUES

Known bugs and gotchas, so no agent re-diagnoses one from scratch. Format per PROJECT_SPEC.md §11.
Close entries by moving them to the bottom under "Resolved" with the fix commit.

## Open
- I005 — Owner's machine: Python 3.11 was uninstalled/moved but the `py` launcher registry
  and user PATH still point at `C:\Users\jaybe\AppData\Local\Programs\Python\Python311\`
  ("Unable to create process… system cannot find the file"). The repo `.venv` is built on
  that base and is therefore broken; this also caused the IDE interpreter-binding failures
  (I004's config is correct but needs a healthy venv underneath).
  Fix (owner or an Antigravity agent with terminal access):
  1. `py -0p` — list actually-registered Pythons.
  2. If a working 3.11+ exists: `py -3.X -m venv .venv --clear`. If not: install 3.11/3.12
     from python.org ("Add python.exe to PATH" + py launcher checked) — overwrites the
     orphaned registry entry.
  3. `.venv\Scripts\activate` → `pip install -r backend\requirements.txt` →
     `python scripts\verify.py` must PASS.
  4. Remove dead `…\Python311\` entries from the user PATH; reload Antigravity and select
     `.venv\Scripts\python.exe`.
  Status: open — close when verify.py passes on a rebuilt venv. Logged 2026-08-11.
  UPDATE (owner's `py -0p`, 2026-08-11): healthy installs exist — **3.10 at
  `C:\Program Files\Python310\`** (use this: `py -3.10 -m venv .venv --clear`, activate,
  reinstall requirements, verify), plus uv-managed 3.14.7 (legit, from prior project) and
  Anaconda 3.9 (below our 3.10 floor — do not use). Only `3.11 *` is orphaned.
  Cleanup for the orphan: delete stale `…\Python311\` user-PATH entries and the registry
  key `HKCU\Software\Python\PythonCore\3.11`. Owner separately wants a fresh 3.12/3.13
  **all-users** install (→ C:\Program Files) as their general Python — needs their UAC
  click; after installing, rebuild the venv on it. This whole item is executable by an
  Antigravity agent with terminal access except the UAC approval.

## Resolved
- I004 — IDE type checkers (Pyrefly/Pyright in Antigravity) reported missing imports
  (e.g. `fastapi.testclient`) despite a working `.venv`: no `pyrightconfig.json` or
  `.vscode/settings.json` existed, so the checker used a bare default environment and
  didn't know `backend/` is the import root. Fixed 2026-08-11: committed
  `pyrightconfig.json` (venvPath/venv/extraPaths) + `.vscode/settings.json`
  (defaultInterpreterPath → `.venv\Scripts\python.exe`). If the interpreter picker still
  errors: Ctrl+Shift+P → "Python: Select Interpreter" → "Enter interpreter path…" →
  paste the full path; then "Developer: Reload Window". Last resort: recreate the venv
  (`py -3.11 -m venv .venv --clear` + reinstall requirements) — a venv whose base Python
  was moved/upgraded breaks interpreter binding.
- I003 — Owner's Windows-installed pre-commit hook (T008) cannot execute inside the Cowork
  Linux sandbox ("cannot run .git/hooks/pre-commit"). Sandbox commits therefore use
  `git commit --no-verify` **only after** an explicit check that `.env` is not staged
  (`git diff --cached --name-only | grep '^\.env$'` must be empty). Secret scanning still
  runs on the owner's machine and in CI (gitleaks job). Logged 2026-08-11.
- I002 — Cowork sandbox egress runs through a SOCKS proxy: httpx needs `pip install socksio`,
  and `alpaca.markets` is not on the sandbox allowlist (ProxyError 403). Consequence: live
  Alpaca integration tests always SKIP inside Cowork; they run for real on the owner's machine
  and anywhere with open egress. Not a code bug. Logged 2026-08-11.
- I001 — git inside the Claude Cowork sandbox cannot delete its own lock/temp files on the
  mounted folder ("Operation not permitted"), leaving a stale `.git/index.lock` that blocks the
  next git write. Fix (Cowork sessions only): call the `allow_cowork_file_delete` tool once,
  then `rm -f .git/*.lock` and delete `.git/objects/**/tmp_obj_*`. Windows/Antigravity/other
  agents are unaffected. Resolved 2026-08-11.
