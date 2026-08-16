# ISSUES

Known bugs and gotchas, so no agent re-diagnoses one from scratch. Format per PROJECT_SPEC.md §11.
Close entries by moving them to the bottom under "Resolved" with the fix commit.

## Open
- I018 [OPEN — CI IS RED, cause not yet identified] (2026-08-16)
  CORRECTION FIRST, because it was mine: Claude repeatedly told the owner "CI has
  been dark" and that T005's push was outstanding. Wrong. `git reflog
  refs/remotes/origin/main` shows real pushes, origin/main == local main (0/0
  divergence), and GitHub Actions has 7 runs. The owner had been pushing all
  along and said so. Claude also claimed CI would have caught the T069
  `captured_at` bug — also wrong, and worse: CI runs the same green pytest suite,
  so it could never have caught it. Only the type checker did.
  THE ACTUAL PROBLEM, found by checking instead of asserting: the `verify` job
  FAILS (exit code 1) on runs #4 (2eff35f, T069) and #7 (b323691, pyrefly) — the
  two checked. `secret-scan` passes. So the gate every agent trusts has been red
  and nobody looked, because the last pushes before today were on 2026-08-11.
  WHAT IS RULED OUT (reproduced, not guessed): a clean venv containing ONLY
  backend/requirements.txt, with the sandbox SOCKS proxy env unset, runs
  `scripts/verify.py` to a PASS — ruff clean, 693 passed, 4 skipped. So it is not
  a missing dependency, not numpy/soundfile (both correctly importorskip'd), not
  the stray root pyproject.toml, and not lint.
  REMAINING SUSPECT: the Python version. CI pins 3.11 (.github/workflows/ci.yml);
  the reproduction above is 3.10, which is all this sandbox has, and `uv python
  install 3.11` cannot reach the network here.
  NOTE the version story is inconsistent across the repo and may itself be the
  bug: AGENTS.md says "Python 3.11+", pyrightconfig.json says 3.10, CI pins 3.11,
  the owner runs 3.14.7, and the stray pyproject.toml declares >=3.14.7.
  NEXT STEP NEEDS THE OWNER (or any agent that can read the log): open
  https://github.com/jaypatel815/KUBERA/actions/runs/31965373918 → the `verify`
  job → the failing step, and paste the traceback. Anonymous access cannot read
  Actions logs, and guessing at a failure whose text is one click away is exactly
  the habit that produced the two corrections at the top of this entry.
- I017 [FOUND 2026-08-16 by a type-checker sweep, NOT yet fixed — owner should decide]
  `LLM_TIMEOUT_SECONDS` does not reach the owner's actual brain. I014 wired the
  knob "through both httpx providers" (anthropic, openai) — accurate as written,
  but the owner's .env says `LLM_PROVIDER=claude-sdk` (I015), and
  `backend/api/llm_claude_sdk.py` contains ZERO occurrences of "timeout". The
  options built at llm_claude_sdk.py:144 pass system_prompt, mcp_servers,
  allowed_tools, disallowed_tools, permission_mode and max_turns — no time limit
  of any kind. So the remediation offered for I014 ("if timeouts repeat, add
  LLM_TIMEOUT_SECONDS=600") is inert on his configuration: a knob he can turn
  that does nothing, which is worse than no knob.
  HOW IT SURFACED: pyrefly flagged `build_provider(s).timeout` in
  test_pacing_timeout.py:76 as "ClaudeSDKProvider has no attribute timeout".
  That specific flag is a FALSE POSITIVE for the test — build_provider returns
  OpenAIProvider/AnthropicProvider for those settings and both carry .timeout
  (verified by running it). But the union member it complained about turned out
  to be a genuine hole in the provider it named.
  NOT FIXED HERE because the right fix is a question, not a line: does the
  installed claude-agent-sdk expose a per-query timeout/cancellation option, or
  must we wrap the async run in `asyncio.wait_for`? The latter works regardless
  of SDK version but needs care so a cancelled query cannot leave a half-written
  assistant row (the I014 recovery path assumes a clean LLMError).
  Suggested ticket: T100 — honor LLM_TIMEOUT_SECONDS in the SDK provider, with
  the same actionable error text as the httpx providers, plus a test that a
  hung query raises LLMError rather than hanging the request.
- I013 [FIXED — verify on owner machine] — "I'd like to update the IPS" → KUBERA
  dumped an 8-row markdown table of INTERNAL parameter names (max_drawdown_frac,
  target_annual_return_frac, ...) and asked the owner to pick fields. Menus and
  schema tables are the opposite of the one-question pacing doctrine. Defenses:
  (1) persona rule "SCHEMAS ARE PRIVATE" — field lists are wiring; the human reply
  is "Sure — what would you like to change?"; long briefs get extraction + action,
  not menus; (2) update_ips description now orders conversational collection and
  forbids displaying its parameter list; (3) deterministic ensure_no_schema_dump
  in chat.py — 3+ distinct underscore-bearing schema property names in a reply
  (when the user neither asked for fields nor used the jargon) → "⚠ Pacing check"
  footer + WARNING log. Owner transcript is a named test. Logged 2026-08-14.
- I015 [DIAGNOSTIC SHIPPED — needs owner's machine] — CORRECTION to the I014/D022
  narrative: the owner's .env says LLM_PROVIDER=claude-sdk (verified 2026-08-14),
  yet the timeout error was produced by the OpenAI-compat provider pointed at
  local Ollama (OPENAI_BASE_URL=localhost:11434, nemotron). Claude wrongly
  asserted "you were on openai" from the error string — the .env said otherwise.
  Both facts are true simultaneously via one of two mechanisms: (a) a real OS
  environment variable LLM_PROVIDER=openai overriding .env (pydantic-settings
  precedence: env vars WIN — now pinned by test_brain_check.py), or (b) a stale
  server process still running with the provider it started with. Shipped:
  scripts/brain_check.py (intent vs resolution vs live server, secrets never
  printed) + startup lifespan log announcing the brain + a loud PROVIDER
  MISMATCH warning when .env intent differs from resolution. Owner: run
  `python scripts/brain_check.py`, then restart the server from a clean shell
  and confirm the startup line says llm_provider=claude-sdk. Logged 2026-08-14.
- I014 [FIXED — verify on owner machine] — the 19k-char IPS brief (I012 resend)
  died with raw "Network error calling openai: ReadTimeout('timed out')" shown to
  the owner (note: provider was openai/local at the time, not claude-sdk). Fixes:
  (1) LLM timeout now settings-driven — LLM_TIMEOUT_SECONDS, default 300s (was
  hard-coded 120s), wired through both httpx providers; timeout errors carry the
  knob's name, never a raw repr; (2) run_chat_turn catches LLMError mid-turn: the
  user message is ALREADY committed before the call, so the reply now says so
  ("saved — say 'try again'"), persists the apology as the assistant row, returns
  stop_reason="llm_error" — thread stays usable, recovery replay is a named test.
  Logged 2026-08-14.
- I012 [FIXED — verify on owner machine] — Owner's full IPS brief (a ~14-section
  message: $1k→$1M goal, horizons, contribution scenarios, drawdown/options policy)
  bounced with `POST /api/chat 422`. Cause: `ChatRequest.message max_length=6000`
  (main.py) — and even if raised alone, `MAX_STORED_CHARS=6000` (chat.py) would have
  silently truncated the stored copy the model replays from history. Fix: request cap
  → 20k, storage cap → 24k (storage > request so user text is never truncated).
  Bonus, same session: the questions inside that message (required CAGR, "2–5%/day",
  contribution comparisons) were unanswerable-with-numbers, so `goal_math` shipped —
  registry tool #25 + `GET /api/goal-math` (analysis/goal_math.py, hand-tested:
  10y needs 99.5%/yr; 1.02^252 ≈ 147x; $500/mo @10% reaches $1M in 29.6y).
  Owner: restart backend, resend the IPS message as-is. Logged 2026-08-14.
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

## I011 — claude-sdk turn denied get_portfolio + hallucinated tool names (2026-08-14)
OBSERVED (owner transcripts, LLM_PROVIDER=claude-sdk per owner): (1) "check my
current portfolio positions" -> model denied having a portfolio tool and listed
NONEXISTENT tools (get_market_data, submit_verdict — distortions of prose, not
real schemas) while the I010 priming HAD fired (footer proved it); (2) rephrasing
to the suggested wording produced a correct morning-brief-style answer. A model
holding real schemas doesn't misspell them; a model with NO tools improvising
from prompt prose does. PRIME SUSPECT: the SDK MCP bridge silently degrading
(version drift) on the owner's machine — some turns get zero tools.
DEFENSES/DIAGNOSTICS SHIPPED:
1. Bridge telemetry: provider logs "claude-sdk: bridged N registry tools" every
   call + WARNING on mismatch; /health now reports llm_provider + tools_registered.
2. Deflection check v3: primed-only trails count as "model called nothing"
   (the denial transcript is a named test); "list the tickers you're holding"
   added to the patterns; portfolio-ish questions asking for tickers now flagged
   even when the user named none (get_portfolio lists them itself).
3. FABRICATION GUARD: if no tool has EVER run in the conversation and none ran
   this turn, yet the reply carries 3+ precise figures absent from the primed
   snapshot -> "⚠ Unverified numbers ... re-ask" footer. Numbers must come from
   tools, never memory.
OWNER VERIFICATION (do once): restart the server; watch the log for
"claude-sdk: bridged 24 registry tools" on a chat turn. If the line is missing
or shows a mismatch: pip install -U claude-agent-sdk and restart. /health also
shows llm_provider + tools_registered for a quick screenshot check.
STATUS: defenses shipped; bridge verification pending on the owner's machine.

## I010 — "check my portfolio for SPY" answered with "how many shares do you hold?" (2026-08-14)
FOURTH strike, same class: the most direct get_portfolio request possible, answered
by asking the user for data the tool holds. The I008 deflection regex didn't fire
(it watched for asks-for-SYMBOL; this asked for shares/cost basis). Prompt rules
(ROUTING, PACING, look-before-asking) demonstrably do NOT stick on the local brain.
ESCALATION — from instructions to architecture:
1. PORTFOLIO AUTO-PRIMING (prime_portfolio in api/chat.py): portfolio intent in the
   user text -> the CHAT LAYER executes get_portfolio server-side and injects a
   compact snapshot into the system prompt ("Answer from THIS data. Do NOT ask for
   share counts...") — deterministic, audited in the trail as auto_primed, feeds
   the recency footer, silent no-op without intent/broker, never crashes the turn.
   Deflection is now structurally impossible for portfolio questions.
2. Deflection detector v2: also fires on asks-for-position-details (shares/cost
   basis/entry price) when the context is portfolio-ish. This transcript is a
   named test.
STATUS: fixed structurally. The pattern (I007-I010) is closed for portfolio asks;
symbol-question deflections still rely on detector + brain quality. claude-sdk
recommendation unchanged; T096 tool-subsetting still queued.

## I009 — record_decision rejected: model sent "None"/""/"BUY" (2026-08-14)
OBSERVED (owner-pasted server logs): two record_decision attempts failed pydantic
validation — the string "None" and empty strings for absent optionals, and a
SHOUTED "BUY" against the lowercase verdict pattern. Silver lining: the T063
persona rule WORKED (the model tried to journal); the arguments were sloppy.
FIX: LenientArgs base model — wildcard before-validator maps ""/"None"/"null"/
"N/A" to real None; verdict lowercased before pattern check. Applied to
record_decision, mark_decision, triage_position, update_ips (the optional-heavy
models). Both failing payloads are now verbatim passing tests; real validation
(bad verdicts, bad numbers) still rejects.
STATUS: fixed. Pattern note: third local-brain formatting issue — T096 (tool
subsetting) and the claude-sdk recommendation stand.

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
## I016 — test_tts_backends.py bare soundfile import broke collection without voice deps (2026-08-16)
OBSERVED (Claude pre-review feedback on shared tree): `backend/tests/test_tts_backends.py`
did a bare module-level `import soundfile as sf`. In basic CI or environments without
requirements-voice.txt installed, pytest collection failed immediately.
FIX (partial): Replaced bare import with `sf = pytest.importorskip("soundfile")` at module
level, allowing pytest to cleanly skip the test suite on lean environments while running on
machines with voice dependencies.
REOPENED 2026-08-16 (Claude, reviewing T072): the fix guards soundfile but NOT numpy.
`import numpy as np` is one line ABOVE the importorskip, and numpy ships in
requirements-voice.txt — never in backend/requirements.txt, which is the only thing
`.github/workflows` installs. So on a clean runner the collection error simply moves from
soundfile to numpy and the whole suite still aborts.
REPRO (verified, not theorised): block numpy with a meta_path hook, then
`python -m pytest backend/tests` →
  `ERROR backend/tests/test_tts_backends.py`
  `ModuleNotFoundError: No module named 'numpy'`
  `Interrupted: 1 error during collection`
Same run with `--ignore=backend/tests/test_tts_backends.py`: 652 passed.
Cross-check that numpy is genuinely absent there: `pip install --dry-run --report` against
backend/requirements.txt resolves fastapi/pydantic-settings/sqlalchemy/alembic/uvicorn/
httpx/pytest/ruff/tzdata and pulls no numpy.
FIX: `np = pytest.importorskip("numpy")` (proven: skips clean without numpy, runs with it).
Better still, move `sf` into `_silent_wav` — six of the eight tests are pure mocks that need
neither library, so CI could actually exercise the backend routing instead of skipping it.
STATUS: RESOLVED 2026-08-16 in `fd1c10c` (Gemini). `np = pytest.importorskip("numpy")` now
precedes the soundfile guard. Verified on the numpy-blocked runner that previously aborted:
671 passed, 4 skipped, module skipping cleanly instead of killing collection.
LESSON WORTH KEEPING: the first fix was correct about the symptom and wrong about the scope —
it guarded the library named in the error and not the one imported above it. When a collection
error is fixed, re-run the failing condition rather than the working one; a green suite on a
machine that has the dependency proves nothing about the machine that does not.

