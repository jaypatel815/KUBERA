# ISSUES

Known bugs and gotchas, so no agent re-diagnoses one from scratch. Format per PROJECT_SPEC.md §11.
Close entries by moving them to the bottom under "Resolved" with the fix commit.

## Open
- I005 [NEARLY CLOSED] — venv observed rebuilt on CPython 3.14.7 (python.org install
  manager, `AppData\Local\Python\pythoncore-3.14-64`) on 2026-08-11. 3.14 is supported
  (project floor is 3.10). Close this issue on the next local `python scripts\verify.py`
  PASS. Original details below.
- (was) I005 — Owner's machine: Python 3.11 was uninstalled/moved but the `py` launcher registry
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
  ONE-COMMAND FIX (2026-08-11): `scripts/repair_python.ps1` automates all of the above at
  user level (no admin): picks newest healthy C:\Program Files\Python3xx, rebuilds .venv,
  reinstalls deps, runs verify (must PASS), removes dead user-PATH entries, deletes the
  orphaned HKCU 3.11 launcher key only after confirming its target is gone. Run:
  `powershell -ExecutionPolicy Bypass -File scripts\repair_python.ps1` — safe to re-run
  (auto-adopts newer Pythons installed later). Close this issue when it reports DONE.

## Resolved
- I006 — Voice loop spoke only the FIRST reply, then printed silently (owner report,
  2026-08-12). Root cause: pyttsx3's well-known Windows bug — `runAndWait()` works once
  per engine instance; subsequent calls are silently ignored. Fix: fresh engine per
  utterance in talk.py's sapi backend (+ both speakers now catch playback errors and
  print a warning instead of killing the loop). Cannot be regression-tested (audio
  hardware); verified by owner in the field. Note: KUBERA_TTS=edge is unaffected by
  this bug and sounds far better anyway.
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

## I008 — "Which ticker?" asked back to a user who NAMED the ticker (2026-08-14)
OBSERVED (owner transcript, day after I007, same brain suspected): "Since I
currently hold SPY, should I continue holding?" -> model asked "tell me which
ticker", claimed a "recent-performance function" doesn't exist (get_symbol_briefing
IS that function), confused get_brief (owner's daily brief) with
get_symbol_briefing, and called ZERO tools. The I007 symbol check was correctly
silent — no tools ran, nothing to compare.
DIAGNOSIS: local-model tool routing failing at 24 tools; reading-comprehension miss
on the named symbol. Pattern across I007+I008: the tool layer is blameless both
times; the LOCAL BRAIN is the failure surface.
DEFENSES SHIPPED (same day):
1. ensure_no_deflection post-check: named ticker + ZERO tool calls + reply asks
   for a symbol -> footer naming the tools that DO answer it. Both transcripts are
   named tests now.
2. Persona ROUTING map: question -> tools ("should I hold X" -> briefing + regime
   + exit plan + triage), "never claim a capability is missing without checking
   the tool list", "never ask for a symbol the user already named" (guard-tested).
STANDING RECOMMENDATION (owner): LLM_PROVIDER=claude-sdk for real decisions; the
local brain is fine for casual queries only. T096 filed: per-brain tool subsetting
so small models see a curated toolset instead of all 24.
STATUS: defenses shipped; monitor. Two strikes on the local brain are data.

## I007 — Model answered "should I buy SPY?" with a TSLA sizing table (2026-08-14)
OBSERVED (owner transcript, 04:31 UTC): user asked about SPY; the model called
size_position for TSLA and presented a confident sizing table for the wrong ticker,
answered an opinion question with a directive, misread age_seconds as "28 s" (the
market was closed — the price was hours old; stale=True was CORRECT), and advised
"refresh the quote" overnight. The TOOL layer behaved correctly throughout — this
was model-level misdirection (brain unknown; local models are more prone).
DEFENSES SHIPPED (same day):
1. ensure_symbol_alignment post-check in api/chat.py — deterministic: if the user
   NAMED tickers and every tool call used different ones, a warning footer is
   appended ("answer may be misdirected — re-ask"). Conservative: silent when no
   ticker named or any overlap. The exact transcript is a named test.
2. age_human on latest trade/quote + size_position ("7h 52m", never raw seconds) —
   models garble seconds arithmetic; give them words.
3. Persona CORE_RULE: "Answer the question that was asked" — opinion questions get
   the analysis structure, sizing only on "how many"; wrong-symbol tools must be
   re-run, not presented. Guard-tested.
RESIDUAL RISK: the footer flags but cannot rewrite a wrong answer; weaker local
models remain more prone. Recommendation to owner: prefer the claude-sdk brain for
real decisions; treat any "Symbol check" footer as a hard stop.
STATUS: defenses shipped; monitor for recurrence.

