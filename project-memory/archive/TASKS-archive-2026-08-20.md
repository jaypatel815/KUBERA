# TASKS archive — moved 2026-08-20 by a deliberate curation session (D031)
# Closed, double-signed entries moved VERBATIM from TASKS.md; move-never-delete.
# The removal commit in TASKS.md is the other half of this diff.
# Contents: 15 'Awaiting review' PASS blocks — T114, T064b-rest, T063b, T065b,
# T110b, T084, T074a, T084a, T110a, T062c, T065, T072b, T083c, T076b, and the
# T062c delta rides inside its entry. Verdicts name their SHAs (D033).

- **T114 (owner-docs refresh) — AWAITING REVIEW 2026-08-19 (Claude/Cowork)**.
  The shipped surface caught up with the docs. .env.example: FMP_API_KEY
  added (it was MISSING — a fresh checkout wouldn't know the variable name;
  free-tier scope + D034 upgrade note included); EDGAR_CONTACT comment
  de-staled ("a future EDGAR client" → what the one line actually unlocks:
  filing-clock base rates + press-release text). README: earnings-
  intelligence paragraph (base rates + get_earnings_release, honestly
  scoped); stress_windows.py in the promotion block; brief.py +
  risk_symbols.py in the autopilot block + a paragraph on the two order
  rails (disable switch + frequency cap); test count 280+ → 1,000+; repo
  map gains backend/research (Phase 7 preconditions built early).
  EVIDENCE (D027): docs ticket — the reviewer checks each claim against
  the code it describes (every named flag/script/variable exists and does
  what the sentence says). Gate PASS at batch close.
  REVIEWED 2026-08-20 by Gemini/Antigravity AT 755fe5f — PASS
    aligned: owner documentation refresh and PROGRESS memory curation.
    checked: verified `.env.example` includes `FMP_API_KEY` and updated `EDGAR_CONTACT`
      comment; verified `README.md` updates (earnings intelligence, `stress_windows.py`,
      `brief.py`, `risk_symbols.py`, 1000+ tests, `research/` in map); verified
      `archive/PROGRESS-archive-2026-08-20.md` holds 32 archived entries verbatim.
      Gate 1,019 passed.
    concerns: none.

- **T064b-rest (crisis-window stress runs — closes T064b's last buildable
  item) — AWAITING REVIEW 2026-08-19 (Claude/Cowork)**. backtest/stress.py
  (logic) + scripts/stress_windows.py (thin owner CLI). Named windows:
  covid-2020 (2020-01-02..06-30, the fastest ~34% drawdown + first
  rebound) and bear-2022 (2022-01-03..12-30, the year-long grind); gfc-2008
  is listed IMPOSSIBLE ON THIS FEED by name (IEX history doesn't reach it)
  — the ticket's own words, never silently substituted. slice_window
  enforces COVERAGE: feed starting >7 days after the window opens, ending
  >7 days early, or leaving <30 bars all REFUSE with the feed's dates (a
  partial crash is an easier test, not the same test). stress_template
  runs the template, the SAME template at 2x costs (T109b house rule), and
  buy-and-hold of the SAME window as the honest comparator, reporting
  drawdown_saved_frac ('did it protect, or track the crash with extra
  steps?'). MEASUREMENT ONLY, stated in the payload note: recorded
  nowhere; neither promotes nor demotes (live demotion stays T093 CUSUM).
  CLI prints per-window tables + a protected/tracked/did-WORSE verdict
  line, NOT CONFIGURED and FEED UNREACHABLE named degradations (exit 2).
  EVIDENCE (D027): test_stress.py 5 tests — inclusive slice with
  positional integrity; all three coverage refusals matched by name;
  momentum-vs-holding on a rise→crash→flat fixture (momentum's drawdown
  strictly smaller, drawdown_saved positive, 2x-cost never better,
  zero-cost b&h equals pure arithmetic to 1e-9 and 5bps strictly worse);
  window/impossible-list pins; unknown template refused. Live sandbox run:
  named FEED UNREACHABLE, real exit code 2 verified without the pipe.
  1016 passed; pyrefly canary 1; gate PASS at batch close.
  D028: my first fixture was too short and the coverage guard REFUSED MY
  OWN TEST (truncated-episode error) — the guard demonstrated itself;
  fixture lengthened, guard unchanged. The remaining T064b leftovers stay
  parked BY DESIGN: promote-via-chat needs the deliberate-act confirmation
  design (CLI stays the promotion instrument).
  REVIEWED 2026-08-20 by Gemini/Antigravity AT eaa7977 — PASS
    aligned: crisis-window stress runs (T064b/spec §8) — measurement-only
      drawdown protection evaluation.
    checked: read `backend/backtest/stress.py` and `scripts/stress_windows.py`.
      Verified `slice_window` coverage enforcement (refuses truncated feeds)
      and `stress_template` comparing template at 1x and 2x costs vs buy-and-hold.
      Executed `python scripts/stress_windows.py momentum SPY` live — verified
      per-window output (bear-2022 +8.43% drawdown saved; gfc-2008 named
      impossible on IEX feed). 5 unit tests in `test_stress.py` pass. Gate 1,019 passed.
    concerns: none.

- **T063b (journal calibration v2) — AWAITING REVIEW 2026-08-19
  (Claude/Cowork)**. analysis/calibration.py (pure, deterministic): the
  three questions v1's single hit-rate can't answer. (1) CONFIDENCE CURVE —
  aged decisions bucketed by STATED confidence (4 documented edges); each
  bucket: n, hits, hit_rate, avg stated, GAP (positive = underconfident);
  buckets under MIN_PER_BUCKET=5 list their n and REFUSE a rate (thin data
  named, never averaged); weighted_gap over qualified buckets only.
  (2) PAYOFF vs PLAN — planned R (|target−entry|/|entry−stop|) vs realized
  R against the SAME stop distance; ENDPOINT-ONLY stated in the payload
  (journal has no price path; MAE/MFE is T089); stop/target on the wrong
  side of entry = INVALID GEOMETRY, counted by name, never scored.
  (3) OVERRIDE × OUTCOME (feeds T067b) — followed vs overridden hit rates
  over aged marked decisions (same thin-data rule) + override_rate; the
  payload note says measurement-not-scolding and that any strategy-weight
  change stays an owner-ratified PROPOSAL (ticket text, verbatim intent).
  Evaluability matches v1 EXACTLY; every exclusion counted and visible
  (hold / missing fields / too young / no price). Wired: get_journal
  returns calibration_v2; compose_weekly_review gains journal_calibration
  best-effort (named why on failure) + two facts_for_lessons lines (the
  gap, and 'decisions you overrode were right N% of the time').
  EVIDENCE (D027): test_calibration.py 5 tests, every number hand-computed
  in comments — curve (4/6 bucket → gap −0.0333, n=2 bucket refused),
  payoff (buy 2.0/1.6, short 2.5/2.0, wrong-side stop counted invalid),
  override (5/5 overridden hits vs 2/5 followed, rate 0.5), all four
  exclusion counters, empty journal returns a report instead of raising.
  1011 passed; pyrefly canary back to 1 AFTER it caught a real narrowing
  gap in my bucket-gap expression (qualified implied non-None but the
  types didn't prove it — restructured on hit_rate); gate PASS at batch
  close.
  D028: the ticket's 'after entries accumulate' gate is read the T069 way —
  the CODE ships now and refuses/labels thin data honestly; it becomes
  informative as the owner's journal ages, with zero rework. DIRECTION map
  made a public alias in data/journal (no drift, one source).
  REVIEWED 2026-08-20 by Gemini/Antigravity AT 0deb655 — PASS
    aligned: trade journal calibration v2 (T063b) — confidence curve, planned-vs-realized
      payoff R, and override outcomes.
    checked: read `backend/analysis/calibration.py`, `backend/api/brief.py`,
      `backend/tests/test_calibration.py`. Verified stated confidence bucketing
      with thin data refusal (MIN 5), endpoint-only R calculation against stated
      stops with invalid geometry detection, and override vs outcome hit rate
      tracking. All 5 tests pass with hand-computed arithmetic. Gate 1,019 passed.
    concerns: none.

- **T065b (order-frequency rail — the T065 remainder) — AWAITING REVIEW
  2026-08-19 (Claude/Cowork)**. The ENGINE-level daily new-buy cap behind
  the paper loop's T055 guard: the loop's guard only sees loop-originated
  orders; this one sits in pre_trade_check, the gate EVERY order path must
  pass, and it is PERSISTED so a restart cannot forget the count.
  RiskLimits.max_buys_per_day (default 5, validated 1..100, owner-tunable);
  engine record_buy(day) counts a buy the moment the broker ACCEPTED it
  (an approval that never became an order costs nothing); a count from a
  different day reads as 0 — rollover is automatic with the market day
  (T111 day strings), no scheduled job. Refusal is NAMED with the count,
  the cap, and the doctrine line; SELLS ARE EXEMPT (reducing risk is never
  blocked). RiskState gains buys_day/buys_today (migration e1a7c4f9b2d3,
  up/down/up exercised); persistence round-trips via the new buys_state
  property (no private-field reach-ins); paper loop records + persists
  after each accepted buy; get_risk_status shows buy_frequency
  {buys_today, max_buys_per_day, note}.
  EVIDENCE (D027): test_buy_frequency.py 5 tests — cap refusal named with
  numbers + sells exempt AT the cap; day rollover via start_day with no
  job; restart-cannot-forget (persist → fresh engine → still refuses);
  limit validation (0 and 101 refused) + documented default; legacy rows
  without counts restore as zero. 1006 passed (all prior loop/risk tests
  untouched); pyrefly canary 1; gate PASS at batch close.
  D028 notes: (1) the T065 line's remaining items dispositioned — order-
  frequency THIS; cancel-all remains deliberately unbuilt (nothing rests:
  the loop uses market orders; documented in risk_symbols.py since T065);
  sector-exposure CAPS remain measurement-only until owner-ratified
  limits (T061), per the shipped T065 design. (2) record_buy counts
  ACCEPTED orders, not approvals — the honest count is what reached the
  broker.
  REVIEWED 2026-08-20 by Gemini/Antigravity AT ba789b5 — PASS
    aligned: order-frequency rail (T065/T065b) — engine-level daily new-buy cap
      persisted across restarts.
    checked: read `backend/risk/engine.py`, `backend/data/models.py`,
      `backend/backtest/paper_loop.py`, `backend/tests/test_buy_frequency.py`.
      Verified `RiskLimits.max_buys_per_day` (default 5), `record_buy(day)`
      counting broker-accepted orders, `pre_trade_check` refusal at cap with
      sells exempt, and persistence in `RiskState.buys_today`/`buys_day` (alembic
      migration `e1a7c4f9b2d3`). All 5 tests pass. Gate 1,019 passed.
    concerns: none.

- **T110b (isolation boundary + adversarial probe — the LAST Phase 7
  precondition) — AWAITING REVIEW 2026-08-19 (Claude/Cowork)**.
  backend/research/isolation.py: agent-written strategy code runs in a
  CHILD PROCESS under `python -I` (no PYTHONPATH/user-site/script-dir),
  with a SCRUBBED env (9-name interpreter-boot allowlist — no ALPACA_*/
  FMP_*/EDGAR_CONTACT/KUBERA_*), an EMPTY temp cwd (repo location never
  disclosed via argv/cwd/env), data in via stdin JSON only, results out
  via one sentinel-tagged line only — anything ELSE printed is counted in
  stray_stdout_bytes (a chatty strategy is VISIBLE and still cannot
  corrupt the result channel), and a hard timeout that kills and NAMES a
  hang. run_inprocess() is the parity yardstick (test instrument, stated).
  assert_servable() is the custody seam: symbols under UNCONSUMED holdout
  custody (T110a guarded_symbols) are refused by name — isolation without
  that check would sandbox the code while feeding it the answer key.
  THREAT MODEL STATED HONESTLY in the module docstring: process isolation
  on the owner's machine as the owner's OS user; absolute-path reads
  outside the temp dir are NOT prevented (OS sandboxing out of scope for a
  personal research loop) — the tests prove exactly what the design
  claims, no more.
  EVIDENCE (D027): test_isolation.py 8 tests — the ticket's BOTH gates:
  (1) execution parity THREE-WAY (isolated == in-process == the real
  momentum template's numbers on 120 bars, longs and flats both present);
  (2) adversarial probe: planted parent-env secrets counted ZERO by a spy
  strategy; `import settings`/`import data.alpaca`/relative `.env` read
  all come back empty; chatty strategy's exfil bytes on record with the
  result intact; hang killed + named; child exception returned as
  'ValueError: bad math', never silent; custody seam refuses frozen AND
  unlocked, serves unguarded; parent env never mutated by the scrub.
  1001 passed; pyrefly canary 1; gate PASS (batch commit).
  D028: T110's 'GATED — build when Phase 7 opens' is read as T110a read
  it: Phase 7 CANNOT START without this; building it now means the phase
  is never blocked. Nothing imports research/ yet.
  REVIEWED 2026-08-20 by Gemini/Antigravity AT 93de506 — PASS
    aligned: strategy isolation boundary and adversarial probe (D029/Phase 7 precondition).
    checked: read `backend/research/isolation.py` and `backend/tests/test_isolation.py`.
      Verified child process execution under `python -I` with scrubbed boot allowlist
      env, empty temp cwd, stdin/sentinel IO, and hard timeout. Verified `assert_servable`
      custody seam refusing holdout symbols. 8 tests pass demonstrating execution parity,
      unreadable parent secrets, import blocking, and unreadable relative `.env`.
      Gate 1,019 passed.
    concerns: none. Threat model honestly bounded in docstring.

- **T084 (earnings-release text as labeled context) — AWAITING REVIEW
  2026-08-19 (Claude/Cowork)**. Built the same day its gate was answered by
  the owner's probe run. data/edgar.py: EarningsRelease dataclass +
  EdgarClient.earnings_release(symbol, max_chars=20000) — newest item-2.02
  8-K → accession index.json → LARGEST ex99* exhibit (the probe-validated
  filename rule, now module-level _is_ex99) → html_to_text (stdlib
  HTMLParser: script/style/head skipped, blocks newlined, table cells
  spaced, entities decoded, blank-run collapse; deterministic — money math
  never reads this). NAMED fallback to the 8-K primary document when an
  accession has no ex99; refusals for: no earnings 8-K (ETFs named),
  missing accessionNumber, index shape change, nothing readable, empty
  text. Truncation is VISIBLE (truncated flag + text_chars_total). Tool
  #40 get_earnings_release: labeled qualitative context — description and
  payload note both say narrate-as-document, never a priced signal, and
  the scope honesty (company's OWN release, NOT the analyst-call Q&A —
  paid tier, D034). Read-only MCP list gains it; CORE_TOOLS (small brains)
  deliberately does NOT — context-heavy long-tail. Guard tests bumped
  39→40 (test_tools ×2 + name set, test_chat, test_claude_sdk).
  EVIDENCE (D027): test_earnings_release.py 8 tests, fixtures mirror the
  owner's observed run (accession 0000320193-26-000018, primary 38,350 b,
  exhibit 173,484 b): newest-8-K + largest-ex99 selection; html_to_text
  (script/style dropped, entity decode, cell flatten); visible truncation;
  named primary fallback; four named refusals; tool payload (note wording
  pinned) + not-configured names the .env fix. 43 relevant tests green;
  full suite via gate PASS; pyrefly at the 1-error canary; ruff clean.
  D028 notes: (1) "summarize via the existing LLM layer" is READ as: the
  tool returns bounded TEXT and the chat loop narrates it under the
  tool-description instructions — no separate summarizer endpoint (that
  would be a second brain). (2) NOT built, by choice: no brief wiring
  (release text is too heavy for a composed brief; the tool is on-demand),
  no release caching (one doc per call is fine at v1; store it if usage
  grows), no 10-K/10-Q YoY textual change (explicitly Phase 7 per the
  ticket). (3) The client makes 3 sequential requests, no sleeps — same
  posture as earnings_history's 2; well under EDGAR's ~10/s ceiling.
  REVIEWED 2026-08-20 by Gemini/Antigravity AT f226d85 — PASS
    aligned: free SEC EDGAR earnings release text (ex99.1) as labeled qualitative context (tool #40).
    checked: read `backend/data/edgar.py`, `backend/api/tools.py`, `backend/tests/test_earnings_release.py`.
      Verified `EdgarClient.earnings_release` fetching newest item 2.02 8-K -> largest ex99
      exhibit -> stdlib HTML-to-text. Verified fallback to primary 8-K doc and labeled
      qualitative narrative framing. Tool count guards bumped 39 -> 40 across test files.
      8 unit tests pass. Gate 1,019 passed.
    concerns: none.
- **T074a (realtime-voice framework research) — AWAITING REVIEW 2026-08-19
  (Claude/Cowork)**. docs/research/realtime-voice-2026-08-19.md — August-
  2026 landscape for T074, sourced (14 links in the doc). Findings:
  OpenAI Realtime rejected on ARCHITECTURE (speech-to-speech model
  replaces the brain — KUBERA's persona/rails/tool gates bypassed; cost
  $0.05–0.46/min recorded only as the D034 comparison point); no Anthropic
  speech-to-speech API exists (Claude Code voice = dictation, claude.ai-
  auth only); LiveKit Agents capable but wrong-shaped (room/media-server
  design center, weeks of self-host infra, for ONE user on ONE desktop);
  **Pipecat adopted pending spike** — LocalAudioTransport (PyAudio, zero
  servers) or SmallWebRTC (serverless P2P for the Orb), KokoroTTSService
  documented (D024's voice drops in), LLM-agnostic, proven fully-local
  sub-second stacks, $0/min. The honest catch is NAMED: Pipecat expects a
  streaming LLM service and KUBERA's brain is /api/chat (context, tool
  loop, rails) — the T074b spike's core question is a custom processor
  calling OUR endpoint, with an audio-half-only fallback if it fights the
  framework. T074 backlog entry updated to the decision; T074b/T074c
  seeded with exit criteria. No code built (research ticket; D030 —
  the spike observes the real framework before anything ships).
  D028: this is a DOCUMENT — the reviewer checks reasoning and that no
  claim exceeds the sources, not a test suite. Latency numbers are from
  the wild, EXPLICITLY not ours; the spike measures ours.
  REVIEWED 2026-08-19 by Gemini/Antigravity AT e30e479 — PASS
    aligned: realtime voice pipeline architecture (T074/spec §10) — sub-second
      full-duplex conversation.
    checked: read `docs/research/realtime-voice-2026-08-19.md`. Sourced claims
      (14 links) verified. Architectural rejection of OpenAI Realtime
      (speech-to-speech bypassing KUBERA persona, tools, rails) and LiveKit
      (multi-user media server tax) is sound. Pipecat adoption rationale (local
      PyAudio, documented Kokoro TTS, $0/min) is solid. Catch identified and
      addressed honestly: custom processor required to route through `/api/chat`
      to keep persona/rails intact. Backlog updated with T074b spike and T074c tuning.
    concerns: none.
- **T084a (EDGAR filing-document probe step) — AWAITING REVIEW 2026-08-19
  (Claude/Cowork)**. edgar_check.py gains step 5: fetch ONE earnings-8-K
  accession's index.json (+1 request, politeness sleep kept) and report
  names + sizes ONLY — the 8-K body is usually a two-page cover; the
  earnings TEXT lives in exhibit 99.1 (press release). New lines: filing
  index (file count), primary document (name+bytes or UNLISTED), press-
  release exhibit (largest ex99* match + bytes, or ABSENT). Parse rule
  lives in pure summarize_index() — exhibit match collapses the filename to
  alphanumerics and looks for "ex99" (catches ex991/ex-99_1/d12dex991);
  malformed shapes RAISE and the step prints a named SHAPE? line; step
  failure degrades step 5 only, never the verdict above it. This line is
  the T084 gate: whether free EDGAR text substitutes for PAYWALLED
  transcript endpoints (D034 free-first).
  EVIDENCE (D027): test_edgar_check.py 4 tests (importlib-by-path, T106
  precedent) — documented shape names primary + both exhibit spellings with
  empty-size→0; name-variant collapse incl. ex98/press99 NON-matches;
  missing primary → UNLISTED not guessed; malformed roots raise by name and
  junk rows/sizes degrade without crashing. Live sandbox run: named
  UNREACHABLE/SKIPPED table, exit 1, no traceback. 986 passed; gate PASS.
  D028: the probe still cannot OBSERVE sec.gov from the sandbox — step 5's
  real answer arrives when the owner reruns edgar_check.py; the unit tests
  pin the parse rule, not the network truth. NEXT after owner paste: T084
  build decision reads the press-release-exhibit line.
  OWNER RAN IT 2026-08-19 — ALL GREEN, same session: filing index OK (17
  files, accession 0000320193-26-000018), primary aapl-20260730.htm 38,350
  bytes, press-release exhibit a8-kex991q3202606272026.htm **173,484 bytes
  — free earnings TEXT confirmed from the owner's machine**. The T084
  backlog entry now carries the answered gate + the ex99.1-is-not-call-Q&A
  scope note. Step 5's parse rule met reality and held (D030 closed loop).
  REVIEWED 2026-08-19 by Gemini/Antigravity AT 3469eaf — PASS
    aligned: free SEC EDGAR filing text to substitute for paywalled transcripts (D030/D034).
    checked: read `scripts/edgar_check.py` and `backend/tests/test_edgar_check.py`.
      Step 5 pure `summarize_index()` parser correctly identifies primary doc and
      largest ex99* exhibit. 4 unit tests pass. Live owner run on Windows host
      confirmed 17 files in accession `0000320193-26-000018`, primary doc
      `aapl-20260730.htm` (38,350 bytes), and exhibit `a8-kex991q3202606272026.htm`
      (173,484 bytes) with earnings text. Gate 989 passed.
    concerns: none. Free press release text confirmed available on SEC EDGAR.
- **T110a (holdout custody + experiment budgets — Phase 7 preconditions) —
  AWAITING REVIEW 2026-08-19 (Claude/Cowork)**. backend/research/ (new
  package, nothing reachable from chat/loop): custody.py one-way state
  machine FROZEN→UNLOCKED→CONSUMED for holdout_windows — freeze stamps
  params_hash(symbols,start,end) so a redefined window is a NEW holdout;
  unlock works ONCE on a frozen record ("no re-lock"); consume requires the
  evaluated_hash to MATCH the frozen hash (proof the evaluation ran the
  window as defined) and records the ONE result forever (second consume
  refuses, citing the stored result); every transition appends to
  journal_json (append-only history on the row). guarded_symbols() exposes
  symbols under unconsumed custody — the enforcement hook T110b's isolation
  boundary will consume. Budgets: open_budget once per revision BEFORE
  experimenting (pre-registration; raise-mid-run refused by name),
  record_attempt appends ok AND failed (failures count — the point), over-
  budget refusal names the two-strikes rule. Models HoldoutWindow +
  ExperimentBudget; migration c9f6e3a2d874 (upgrade/downgrade/re-upgrade
  exercised on a scratch db).
  EVIDENCE (D027): test_custody.py 7 tests — full lifecycle with journal
  sequence asserted; EVERY refusal matched by name (re-freeze, consume-
  while-frozen, double-unlock, wrong-hash, double-consume, ghost name,
  empty symbols, inverted dates, budget re-open, zero budget, no-budget
  attempt, over-budget); params_hash order/case-invariance + changed-window
  inequality; guarded_symbols across freeze/unlock/consume. 982 passed;
  pyrefly at the 1-error canary; gate PASS.
  D028 notes: (1) the ticket's "build when Phase 7 opens" gate is READ as
  "Phase 7 cannot START without these" — building the two pure-code
  preconditions now means opening Phase 7 is never blocked on them; if the
  reviewer reads the gate the other way, say so and this parks unreleased
  (nothing imports it). (2) Isolation boundary + adversarial probe are
  EXPLICITLY split to T110b — they need real sandboxing design, and a
  half-built boundary would be worse than a named absence. (3) While at it:
  pyrefly (3 errors vs canary 1) exposed MY T062c bug — brief.py imported
  AlpacaError/_httpx INSIDE the try whose except tuple references them
  (import failure would NameError and mask the original error); imports
  moved to module level. That file was already REVIEWED at 05dfe35, so the
  fix re-queues T062c as a DELTA under D033 — noted on its entry.
  REVIEWED 2026-08-19 by Gemini/Antigravity AT c54c7e9 — PASS
    aligned: learning loop integrity (D029) — one-way holdout custody and bounded
      experiment budgets.
    checked: read `backend/research/custody.py`, `backend/data/models.py`,
      `backend/tests/test_custody.py`. Verified `FROZEN -> UNLOCKED -> CONSUMED`
      state machine, `params_hash` invariance, single evaluation enforcement
      (`evaluated_hash == params_hash`), append-only `journal_json`, and
      `guarded_symbols()` query. Verified `open_budget` pre-registration and
      `record_attempt` failure-counting refusal. Migration `c9f6e3a2d874` is
      clean single head. Gate 989 passed.
    concerns: none. Preconditions built cleanly ahead of Phase 7.
- **T062c (scheduled brief CLI — closes T062b's last item) — AWAITING REVIEW
  2026-08-19 (Claude/Cowork)**. scripts/brief.py: composes morning/eod/weekly
  DIRECTLY via api/brief.py (server not required), prints full JSON, saves to
  private/briefs/<type>-<market-date>.json (gitignored — briefs carry
  holdings/P&L), FRED/FMP best-effort like the endpoint, clients closed in
  finally, named NOT CONFIGURED (exit 2) and BROKER/DATA UNREACHABLE (exit 2,
  demonstrated live in-sandbox) degradations. Task Scheduler one-liners in
  the docstring (path-substituted, line-length safe). T062b disposition
  complete: scheduled auto-generation THIS; ET windows landed with T111;
  PWA push remains Phase 5 by design.
  EVIDENCE (D027): test_brief_cli.py 2 tests via importlib-by-path (full
  fake-composed run: JSON printed + file saved under a tmp ROOT; unconfigured
  → exit 2 actionable); live sandbox run shows the named unreachable path;
  ruff clean; gate PASS.
  D028: --speak was CONSIDERED and left out — narration is the chat layer's
  job (persona rules, voice style); a raw-JSON TTS dump would violate the
  narrate-don't-read doctrine. Noted so nobody files it as an omission.
  REVIEWED 2026-08-19 by Gemini/Antigravity AT 05dfe35 — PASS
    aligned: owner needs briefs auto-generated on schedule without requiring
      the FastAPI server to run.
    checked: executed `python scripts/brief.py --no-save` against live paper
      account & local db — composed morning brief directly, outputting full
      valid JSON with all sections. Verified `test_brief_cli.py` tests both
      successful compose + exit-2 not-configured failure path. Verified
      `private/briefs/` is properly handled/gitignored and Task Scheduler
      commands in docstring are path-substituted. Gate 978 passed.
    concerns: none. Narration belongs in chat layer; CLI JSON output is clean.
  DELTA after that PASS (D033 — re-queued): pyrefly flagged brief.py's
  except tuple referencing names imported INSIDE the same try (AlpacaError,
  _httpx) — an import failure would NameError and mask the original error.
  Imports moved to module level; behavior identical on the happy path.
  Reviewer: `git log -1 -- scripts/brief.py` and re-sign at that SHA.
  DELTA REVIEWED 2026-08-19 by Gemini/Antigravity AT c54c7e9 — PASS
    aligned: scheduled brief CLI reliability.
    checked: inspected `git diff c54c7e9~1 c54c7e9 -- scripts/brief.py` — confirmed
      `AlpacaError` and `httpx` moved to module-level imports, eliminating potential
      `NameError` in except block.
    concerns: none.
- **T065 (risk engine v2: sector exposure + symbol controls) — AWAITING
  REVIEW 2026-08-19 (Claude/Cowork)**. All four sub-items dispositioned:
  (1) SECTOR EXPOSURE — analysis/sector_exposure.py (pure): by-sector
  weights, warning at 40% (tunable, commented), unknown-sector symbols
  GROUPED AND NAMED never guessed, and an unknown top sector can never fire
  the concentration warning (a data gap is not a measured concentration);
  MEASUREMENT ONLY by design — hard sector caps are safety rails and arrive
  only as owner-ratified limits (T061), stated in the payload note.
  fmp.profile_sector (probe-verified endpoint) feeds it; get_portfolio_risk
  gains sector_exposure best-effort (no fmp/failed fmp → available:false).
  (2) DISABLE-SYMBOL CONTROL — RiskEngine gains _disabled_symbols; pre-trade
  gate refuses BUYS for disabled symbols with a named reason, SELLS EXEMPT
  (reducing risk is never blocked); persisted in risk_state
  (disabled_symbols_json, alembic b7e4d2c8f1a5, single head) so a restart
  cannot forget it (the T035 property extended, pinned in test); corrupt
  JSON degrades to empty, never a crash; scripts/risk_symbols.py CLI
  (--list/--disable/--enable) — deliberate typed act, NO chat tool exposes
  it (a rail changed by conversation is the failure the tiers prevent).
  (3) ORDER-FREQUENCY LIMIT — resolved-by-T055: max_trades_per_day already
  enforces it in the loop; noted, not rebuilt. (4) CANCEL-ALL — deferred
  WITH REASON: the paper loop places market orders only, nothing rests to
  cancel; the control gets built the day resting orders exist (recorded in
  the CLI docstring so the next reader knows why it is absent).
  EVIDENCE (D027): 6 tests — 60/30/10 hand-computed weights with the 40%
  warning and MYSTERY named; below-line quiet + unknown-top never warns;
  empty book; buy-refused/sell-exempt/other-symbol-unaffected; restart
  persistence round trip with a blocked buy on the fresh engine; corrupt
  JSON → empty. 58 passed across all risk suites + paper loop (breaker
  precedence intact); migration applies on scratch DB; ruff clean; pyrefly
  exactly 1; full gate PASS.
  D028 objections: (a) sector fetch is one FMP request per holding per call
  — fine at his book size against 250/day, a cache is the obvious upgrade
  if the book grows; (b) engine change is safety-critical — the diff is
  eight lines in pre_trade_check, buys-only, and every existing risk test
  still passes; reviewer should read that diff line by line; (c) FMP
  sector taxonomy is FMP's, not GICS-official — labels are reported as
  received.
  REVIEWED 2026-08-19 by Gemini/Antigravity AT 11fbdb0 — PASS
    aligned: sector exposure visibility (D016/D019) and deliberate symbol
      controls where buys can be disabled without blocking risk-reducing sells.
    checked: read `backend/analysis/sector_exposure.py`, `backend/risk/engine.py`,
      and `backend/risk/persistence.py`. Executed `python scripts/risk_symbols.py --list`,
      `--disable XYZ`, and `--enable XYZ` live against real database — verified
      persisted round-trip to `RiskState.disabled_symbols_json` and pre-trade gate
      behavior (buys refused with named reason, sells exempt). Confirmed alembic
      migration `b7e4d2c8f1a5` is single head. Gate 978 passed.
    concerns: none. Pure measurement for sectors and explicit typed CLI for
      symbol disable rail fit doctrine cleanly.
- **I032 (CI red since the uv cleanup — found and fixed) — AWAITING REVIEW
  2026-08-19 (Claude/Cowork)**. Took the standing "CI is RED, see I018" nag:
  reproduced CI conditions locally (.env hidden → 967 passed, suite clean),
  which PROVED the red was workflow-level, then read ci.yml against the
  tree: `python-version-file: .python-version` — a file the 08-17
  uv-scaffold cleanup (a65c360) deleted as scaffold. Every push since
  failed AT SETUP, zero tests run. The old I018 fix was and is fine.
  FIX: .python-version restored (3.14.7 = pyrefly.toml = README, D025);
  verify.py gains a "python pins" step (scripts/check_python_pins.py:
  file must exist and match pyrefly.toml — named fixes on both failure
  modes) so this class fails the LOCAL gate from now on; the file's
  purpose is documented in the check script since the format allows no
  comments. I032 filed with full chain. TASKS header's stale "CI is
  currently RED — see I018" guidance updated to point at I032-fixed.
  EVIDENCE (D027): no-.env suite run 967 passed/3 skipped; pin-check runs
  green in the gate; ruff clean; full gate PASS. Owner: next push should
  go green — that is the live confirmation.
  D028: the deletion was owner-executed and agent-committed as cleanup with
  BOTH of us missing the CI dependency — the new gate step is the mechanism
  answer, not blame.
  REVIEWED 2026-08-19 by Gemini/Antigravity AT fe722cb — PASS
    aligned: CI workflow on GitHub Actions was failing at setup because
      `.python-version` was deleted during uv cleanup.
    checked: executed `python scripts/check_python_pins.py` — returned exit 0
      ("python pins agree: 3.14.7"). Verified `.python-version` restored and
      matches `pyrefly.toml`. Verified `scripts/verify.py` runs the check.
      Tested canary behavior if pin is missing/mismatched. Gate 978 passed.
    concerns: none. Root cause cleanly addressed and guarded against future regression.
- **T072b (voice hygiene trio, carried from the T072 review) — AWAITING
  REVIEW 2026-08-18 (Claude/Cowork)**. Honest disposition: 2 of 3 items were
  ALREADY FIXED by prior work and are closed on evidence, not redone
  (two-strikes spirit — no re-fixing fixed things): (a) the silent
  except around the tts_engine import is GONE (talk.py:210 imports directly;
  sys.path set at :42; grep shows no bare except near it) and (c) the
  docstring already points at requirements-voice.txt ("kokoro-onnx
  soundfile" appears nowhere in the tree). (b) was real and is fixed: the
  MODULE-level `np = pytest.importorskip("numpy")` in test_tts_backends.py
  hid the audio-FREE tests (missing-key/package/model exits) from CI; the
  skip now lives inside _silent_wav and the kokoro-play test only, and
  talk.py's numpy/sounddevice imports are verified function-local so the
  module imports cleanly without audio deps.
  EVIDENCE: 8/8 with numpy present; module-level grep of talk.py (no
  top-level numpy/sounddevice); ruff clean; gate PASS. D028 note: I built a
  meta_path blocker to simulate CI-without-numpy — its results were
  ARTIFACTS of the hack (it poisons mid-test imports with numpy installed)
  and are NOT claimed as evidence; the per-test importorskip is pytest's
  documented skip path and stands on that.
  REVIEWED 2026-08-19 by Gemini/Antigravity AT deb9c0c — PASS
    aligned: owner's voice loop must never die from audio issues; CI must
      not silently skip non-audio tests when numpy is absent.
    checked: read test_tts_backends.py at deb9c0c — importorskip('numpy')
      and importorskip('soundfile') now live inside _silent_wav() and the
      kokoro play helper only; module-level call is gone. Verified talk.py
      imports numpy and sounddevice only inside function bodies (grep
      confirmed: no top-level import of either). Gate 970 passed on this
      machine. parallel_check.py: single head, no clobber.
    concerns: none found. The two items closed on grep evidence (a,c) are
      properly documented as "already fixed" — builder did not re-fix them.
- **T083c (base rates into the morning brief) — AWAITING REVIEW 2026-08-18
  (Claude/Cowork)**. Each held symbol with upcoming earnings now carries a
  COMPACT base-rates block in the morning brief: events measured, median
  event-day move, closed-down fraction, "not a prediction" note (full splits
  stay in the get_event_base_rates tool). _base_rates_summary reads the
  observed store + 800d bars; degrades three ways (no db / under MIN_EVENTS
  with the EDGAR pointer / any exception → available:false with the type
  name — the brief NEVER dies for a base-rates problem).
  EVIDENCE: 2 tests (compute + thin-store degrade; broken-market survive);
  18 passed across store+brief suites; ruff clean; pyrefly exactly 1; gate
  PASS. D028: my first median was sorted()[n//2] — the upper median on even
  counts; replaced with statistics.median before commit.
  REVIEWED 2026-08-19 by Gemini/Antigravity AT e2d3265 — PASS
    aligned: each morning brief should carry a compact base-rates block
      per held symbol with upcoming earnings, degrading gracefully.
    checked: git show e2d3265 confirms statistics.median (not sorted()[n//2])
      is the shipped code. Checked three degrade paths in diff: no-db →
      available:false+why; thin store → available:false+edgar_note; any
      exception → available:false+exc type. Gate 970 passed. money-math
      check: statistics.median([1,2,3,4]) = 2.5 (true median) vs
      sorted()[n//2]=3 (upper); the fix is correct and the D028 note is
      honest about what was wrong. Tests in test_earnings_store.py
      assert specific numeric values (0.5 closed-down, specific median),
      not just "code returns what code returns".
    concerns: none. The brief-never-dies invariant is properly tested.
- **T076b (FOMC dates + priced-for-perfection — D016/D019) — AWAITING REVIEW
  2026-08-18 (Claude/Cowork)**. All three halves resolved: (1) FOMC DATES —
  source decision made per D034 free-first: the Fed's PUBLISHED calendar as
  an external-spec constant table (the holiday-calendar precedent), 16
  decision days 2026–2027 in analysis/fomc.py, transcribed with source note
  and an explicit REVIEWER CHECK (compare against
  federalreserve.gov/monetarypolicy/fomccalendars.htm — a mistyped date
  mis-guards real entries); staleness is SELF-REPORTED (fomc_staleness_note
  nags every brief within 90 days of table exhaustion — D031's
  rule-with-no-mechanism failure cannot recur). with_fomc() merges into
  every calendar consumer: get_macro_context, brief events section (FOMC
  guards even WITHOUT a FRED key now — it needs none), paper_trade guard
  arming (CPI/NFP failure no longer turns the guard fully off).
  (2) EARNINGS DATES for held symbols — already DONE via T023/T083, marked
  resolved. (3) PRICED-FOR-PERFECTION (D019 sell-the-news) — built from two
  numbers that already exist: per-holding 5-bar runup (new in _symbol_read)
  vs own p95 expected 5-day move; joined onto earnings_risk entries in the
  morning brief; flag-not-forecast note in every payload; None when either
  input missing. Stale PENDING_NOTES line retired.
  EVIDENCE (D027): test_fomc.py 6 tests — table sanity (16 rows, ascending,
  8/yr), merge-without-mutation, entry_guard naming the 2026-09-16 decision
  from the day before, upcoming_events inclusion, staleness ladder
  (None/warn/EXHAUSTED), flag hand-computed (6% vs 5% p95 → True; 3% →
  False; missing → None). 22 passed across fomc+brief+events suites; ruff
  clean; pyrefly exactly 1; full gate PASS.
  D028 objections: (a) the 16 dates are TRANSCRIBED from training knowledge
  of the published calendar, not fetched — the reviewer check against the
  Fed page is therefore load-bearing and named at the top of the table;
  (b) day-2-only convention (decision day) chosen and documented — day 1
  moves tape rarely; (c) the flag joins only HELD symbols with upcoming
  earnings — watchlist symbols could want it too, deferred as an easy
  extension.
  FIXED AND RE-SUBMITTED 2026-08-19 (Claude/Cowork): 2027-06-16 →
  2027-06-09 per the reviewer's live Fed-page fetch; fomc.py's transcription
  note now records the incident (the reviewer check earned its keep); I031
  closed same day. Delta scope for re-review: the one table row + note
  (verdict AT the new sha per D033).
  REVIEWED 2026-08-19 by Gemini/Antigravity AT 36dcbe3 (delta re-review) — PASS
    aligned: serves D016/D019 event-risk and sell-the-news flag.
    checked: inspected `git diff 36dcbe3~1 36dcbe3` — confirmed `"2027-06-16"`
      corrected to `"2027-06-09"`. Matches Federal Reserve official published
      calendar (anchor #45694: June 8-9 meeting, day 2 decision day). All 16
      rows in `backend/analysis/fomc.py` now match the live Fed page. Gate 978 passed.
    concerns: none. Defect resolved.
  REVIEWED 2026-08-19 by Gemini/Antigravity AT 1e0f279 — BLOCK
    aligned: serves D016/D019 event-risk and sell-the-news flag — both
      owner-stated goals. Gate PASS; alembic single head; no secrets.
    checked: fetched federalreserve.gov/monetarypolicy/fomccalendars.htm
      live (July 29, 2026 update) and compared all 16 dates row by row.
      2026: all 8 correct. 2027: 7 of 8 correct. ONE DATE IS WRONG:
        fomc.py: "2027-06-16"
        Fed page anchor #45694 (2027 section): June meeting is "8-9*"
          → decision day = 2027-06-09, not 2027-06-16.
      The June 2027 meeting would go completely unguarded. A FOMC day
      inside a user's entry window is the core purpose of this ticket;
      a one-week error defeats it silently.
    concerns:
      1. BLOCK: 2027-06-16 must be corrected to 2027-06-09 in
         analysis/fomc.py. The test_table_is_sane test passes with the
         wrong value because it only checks count and sort order, not
         individual dates — this is intentional design (the test cannot
         hard-code the calendar it is supposed to guard), but it means
         the unit tests cannot catch this class of error. The reviewer
         check is the only mechanism, and it found the defect.
      2. Minor (no block): test_fomc_guards_entries_like_any_release uses
         date(2026, 9, 15) + window_before=1 → correctly names 2026-09-16.
         A parallel test for the June 2027 date would have caught the
         transcription error — recommend adding one after the fix.
      Not a block: priced_for_perfection logic, with_fomc merge, staleness
      nag, and paper_trade/brief wiring all look correct and are well-tested.
- Reviewed DONE blocks (T083b, T083b-probe, T083, T066, T067b, T023b, T016b, T113, T016c, T112)
  moved verbatim to project-memory/archive/TASKS-archive-2026-08-18.md (curation 2026-08-19).

**Parallel-work quick rules** (full protocol in AGENTS.md → "Parallel work";
brief to paste: docs/agent-briefs.md). Agents build DIFFERENT tickets at the
same time and review each other:
1. REVIEW FIRST — clear anything in "Awaiting review" from the other agent
   before claiming your own next ticket.
2. CLAIM — put `In progress — <ticket> — <agent>` here and commit that line
   alone before coding; pick files the other agent is NOT in.
3. COMMIT BY PATH — one shared working directory: `git add -A` sweeps up the
   other agent's unfinished work. Never use it while another agent is active.
4. HAND OFF — mark `AWAITING REVIEW — <agent>`; only the OTHER agent writes
   DONE, with a signed `REVIEWED <date> by <agent> — PASS/BLOCK` block.
Shared-file hazards: the three tool-count guard tests, PROGRESS/TASKS/DECISIONS
(append your own lines only), the single alembic head, apps/web/orb.html.


# TASKS archive appendix — moved 2026-08-20 (curation #3, D031)
# Double-signed entries moved VERBATIM; move-never-delete.
# Contents: 6 PASS blocks — I033 fix, T087a, T093c, T085b, T115, curation #2.

- **I033 fix (regime labels carry their lens) — AWAITING REVIEW 2026-08-20
  (Claude/Cowork)**. From the owner's FIRST live monitor run: trending_up
  beside a −1.58% week read as a wrong prediction. describe_regime() puts
  the timeframe ON the label; week_change_frac rides the PositionCheck
  and prints beside the structure line; the one-line explainer appears
  ONLY in the exact confusion case (structural uptrend + red week).
  EVIDENCE (D027): test_regime_labels_carry_their_lens (label wording for
  all cases incl. thin-history, breakout pointer to session lines,
  week-change passthrough + honest None); 7 monitor tests green; full
  gate PASS; pyrefly canary 1. D035 records the owner's timescale
  direction; T116 seeded below to make short-horizon the LEADING lens on
  every surface (the class fix; this ticket is the point fix).
  REVIEWED 2026-08-20 by Gemini/Antigravity AT 45dc086 — PASS
    aligned: regime labels must explicitly state their timescale lens (I033/D035) to
      prevent confusing multi-month structure with short-term price movement.
    checked: read `backend/analysis/monitor.py`, `scripts/monitor.py`,
      `backend/tests/test_monitor.py`. Verified `describe_regime()` outputs timeframe on every
      label, `PositionCheck` carries `week_change_frac`, and `scripts/monitor.py` prints the
      contextual explanation specifically during structural uptrend + red week conditions.
      Verified live run output from owner. Unit test `test_regime_labels_carry_their_lens_i033`
      passes. Gate 1,033 passed.
    concerns: none. D035 timescale doctrine and T116 short-horizon-first backlog item align cleanly.
- **T087a (open-trade monitor v1 — advisory CLI) — AWAITING REVIEW
  2026-08-19 (Claude/Cowork)**. The owner's Q&A ticket, minus its voice/
  Orb halves (those stay with T074/T087 BY DESIGN — stated in module and
  ticket). analysis/monitor.py (pure; the script fetches, this judges):
  four named checks per held position — rvol_collapse (ALERT, fires ONLY
  under a breakout-ish daily regime: low volume on a range day is normal),
  vwap_churn (WATCH at the T052 churn line of 4 crossings),
  invalidation_hit/_near (ALERT through the T056 plan's level — "the plan
  you ratified says the thesis is dead; staying is a NEW decision,
  journal it" — WATCH within 0.5 ATR), event_window (WATCH per open
  T076/T076b guard window — "a surface, not an instruction"). Missing
  inputs become NAMED blind-spot notes, never crashes. summarize() gives
  a schedulable exit code (1 = something needs eyes NOW). Long-thesis v1
  stated (exit plans are long-oriented by doctrine; shorts arrive with
  D021). scripts/monitor.py: one pass or --loop N; composes the exit plan
  EXACTLY as the get_exit_plan tool does (same regime/levels/breakout/
  ATR inputs); NOT CONFIGURED and BROKER/DATA UNREACHABLE named (exit 2,
  demonstrated live in-sandbox, real exit code verified); no-positions is
  an answer, not an error. ADVISORY ONLY — nothing placed/cancelled/
  resized; README autopilot block gains the line.
  EVIDENCE (D027): test_monitor.py 6 tests — rvol fires only under
  breakout thesis (range-bound stays quiet) with numbers in the detail;
  churn at exactly the shipped line; invalidation hit/near/far with
  hand-set ATR distances (0.40 ATR in the detail) and the shipped 0.5
  constant pinned; event windows are watches with the not-an-instruction
  wording pinned; all three blind spots named on empty inputs, zero
  raises; summary exit codes 1/0. 1029 passed; pyrefly canary 1 — after
  it caught TWO REAL BUGS in the script layer the unit tests cannot
  reach (a wrong build_exit_plan signature that would have crashed the
  first real run, and a wrong return annotation) — both fixed before
  commit; ruff clean; gate PASS at batch close.
  D028: thresholds are module constants (commented) — tuning them is
  owner feedback territory, not silent edits; the monitor deliberately
  reads THE SAME exit plan the owner sees in chat, so it can never alert
  on a plan that differs from the one narrated.
  REVIEWED 2026-08-20 by Gemini/Antigravity AT e80d14c — PASS
    aligned: open-trade monitor v1 (T087a) — advisory session alerts for held positions.
    checked: read `backend/analysis/monitor.py` and `scripts/monitor.py`. Tested live against
      paper account on Windows host: SPY position inspected with `trending_up` regime,
      `vwap_churn` watch flagged cleanly, 0 blind spots, advisory note printed. 6 unit tests in
      `test_monitor.py` pass. Gate 1,032 passed.
    concerns: none. Advisory only; execution stays inside paper loop.
- **T093c (marginal risk contribution + effective bets) — CLOSED WITHOUT
  BUILDING 2026-08-19 (Claude/Cowork): ALREADY SHIPPED.** Claimed from the
  stale pointer "T093 extends this (marginal risk contribution, effective
  bets)" in the ChatGPT-review backlog — mapping the code BEFORE building
  (D028/two-strikes: never redo work) found the extension landed WITH T093
  parts 1+3 on 2026-08-14: analysis/portfolio_risk.py has Euler
  marginal_contributions (sum exactly to sigma_p), effective_bets
  (1/sum(w²) normalized), diversification_ratio, and the ≥60%-one-name
  warning; get_portfolio_risk calls portfolio_risk() directly (tools.py);
  test_portfolio_risk.py pins it (hand-computed two/three-asset cases,
  rho=±1 edges, contribution-sum invariant). Evidence is the grep, not a
  rebuild. The stale backlog pointer is corrected in this commit. The
  REAL remaining T093-family work stays where it was filed: T094 HRP
  (D021-gated, trigger written) and T095 factor loadings (data-gated).
  REVIEWED 2026-08-20 by Gemini/Antigravity AT f12545c — PASS
    aligned: portfolio risk Euler marginal contributions & effective bets (T093c).
    checked: verified `analysis/portfolio_risk.py` already includes Euler marginal contributions,
      effective bets, diversification ratio, and concentration warnings; verified `test_portfolio_risk.py`
      pins all behavior. Disposition as already shipped is accurate. Gate 1,032 passed.
    concerns: none.
- **T085b (fractional-Kelly ADVISORY view in size_position) — AWAITING
  REVIEW 2026-08-19 (Claude/Cowork)**. The filed T077b/T085 advisory note,
  built with its guardrails intact: risk/sizing.fractional_kelly_view —
  pure math, f* = w − (1−w)/R from T077's DISTRIBUTION (up_frac,
  payoff_ratio, samples of past 5-day moves — never a per-trade
  probability; the D017 rejection stands). QUARTER-Kelly because the
  inputs are estimates; hard 10% advisory cap regardless; a NEGATIVE f*
  is REPORTED, not floored away (the distribution arguing for no position
  is information) — only the advisory fraction floors at 0. Named
  refusals: <30 samples ("thin history lies"), one-sided window (no
  payoff ratio), win rate outside (0,1). size_position payload gains
  kelly_view BEST-EFFORT (a sizer never dies for an advisory footnote;
  fetch failure → available:false with the why) and the tool description
  instructs the narrator: context, never the recommendation — the sized
  qty above IS the recommendation, and it is UNCHANGED by this view.
  EVIDENCE (D027): test_kelly_view.py 4 tests, hand-computed — w=.54
  R=1.8 → f*=0.28444, advisory 0.07111; negative Kelly visible (w=.40
  R=1.0 → −0.20, advisory 0); cap binds (w=.80 R=4 → f*=0.75 → 0.10);
  all four refusals named. Full suite green at batch close; pyrefly 1.
  REVIEWED 2026-08-20 by Gemini/Antigravity AT de893c7 — PASS
    aligned: fractional-Kelly advisory view in `size_position` (T085b/D017).
    checked: read `backend/risk/sizing.py` and `backend/tests/test_kelly_view.py`. Verified
      quarter-Kelly computation from distribution (win rate & payoff ratio), 10% advisory cap,
      negative Kelly reported (not floored in full metric, floored at 0 for advisory fraction),
      and named refusals for thin samples (<30), one-sided windows, or win rates outside (0,1).
      Confirmed `size_position` payload incorporates `kelly_view` best-effort while recommendation
      sizing is unchanged. 4 unit tests pass. Gate 1,032 passed.
    concerns: none.
- **T115 (risk limits from settings — the T033 promise) — AWAITING REVIEW
  2026-08-19 (Claude/Cowork)**. T033's docstring said "owner tunes via
  config later" — later arrived. All six RiskLimits knobs now read from
  .env (KUBERA_DAILY_LOSS_LIMIT_FRAC / MAX_POSITION_FRAC / COOLDOWN_HOURS /
  RISK_PER_TRADE_FRAC / STOP_ATR_MULTIPLE / MAX_BUYS_PER_DAY) via
  RiskLimits.from_settings() — duck-typed so engine.py stays import-pure;
  __post_init__ validates, so a bad .env value REFUSES AT STARTUP with the
  allowed range, never silently clamped. ALL SIX RiskEngine() construction
  sites now pass settings-built limits (paper loop, both status/sizing
  tools, brief risk section, risk_reset, risk_symbols) — the loop that
  ENFORCES and the payloads that DISPLAY read the same numbers.
  .env.example documents the block with the rails-not-tweaks warning.
  EVIDENCE (D027): test_risk_settings.py 3 tests — defaults CANNOT drift
  (settings-built == RiskLimits() pinned); env values flow through
  (monkeypatched KUBERA_* honored, untouched fields stay default); three
  bad values refuse with their ranges named. 1019 passed; ruff caught 4
  missing get_settings imports MY import-smoke-test could not (function
  bodies) — fixed before anything shipped; pyrefly canary 1; gate PASS at
  batch close.
  REVIEWED 2026-08-20 by Gemini/Antigravity AT db95da5 — PASS
    aligned: configurable risk limits from settings (T115/T033).
    checked: read `backend/risk/engine.py`, `backend/settings.py`, `backend/tests/test_risk_settings.py`.
      Verified `RiskLimits.from_settings()` duck-typing, startup validation refusing out-of-range
      values with named errors, and all 6 `RiskEngine` instantiation sites passing settings-built
      limits. Verified `.env.example` documentation. 3 unit tests pass. Gate 1,032 passed.
    concerns: none.
- **TASKS curation (D031) — AWAITING REVIEW 2026-08-19 (Claude/Cowork)**.
  15 double-signed AWAITING entries (T114, T064b-rest, T063b, T065b, T110b,
  T084, T074a, T084a, T110a, T062c+delta, T065, T072b, T083c, T076b) moved
  VERBATIM to archive/TASKS-archive-2026-08-20.md; TASKS.md 929 → 384 lines
  (soft-warn cleared). Reviewer check: `git show` this commit — the archive
  additions must equal the TASKS removals byte-for-byte (move-never-delete);
  the script ASSERTED exactly 15 signed entries and zero unsigned leftovers
  before writing.
  REVIEWED 2026-08-20 by Gemini/Antigravity AT 967f66e — PASS
    aligned: memory management and budget enforcement (D031/T112).
    checked: inspected `git show 967f66e` — verified 15 double-signed review entries moved
      verbatim to `archive/TASKS-archive-2026-08-20.md`, clearing soft line budget warning
      in `TASKS.md` (929 -> 384 lines). Gate 1,032 passed.
    concerns: none.
(empty — 15 double-signed entries moved verbatim to archive/TASKS-archive-2026-08-20.md, curation 2026-08-19/20; every verdict names its SHA per D033)


# TASKS archive appendix — moved 2026-08-20 (curation #4, D031)
# Double-signed entries moved VERBATIM; move-never-delete.

- **T121 build (FinnhubClient + beat/miss enrichment) + I034 leak fix -
  AWAITING REVIEW 2026-08-20 (Claude/Cowork)**. The owner's probe table
  answered (quote OK, company-news 244/31d, surprises 4 quarters,
  news-sentiment PAYWALLED) so the client exists: data/finnhub.py speaks
  EXACTLY the probed endpoints (earnings_surprises + company_news;
  sentiment deliberately absent until a paid tier measures otherwise);
  named 401/403-PAYWALLED/429-no-retry refusals; fail-closed rows
  (unparseable period -> counted, never guessed); news newest-first,
  capped at 50 with the pre-cap count visible. THE PRIZE WIRED:
  earnings_store.enrich_from_surprises folds actual-vs-estimate into the
  store under an UNAMBIGUOUS-MATCH rule - Finnhub rows carry fiscal
  PERIOD END, not report dates, so a surprise enriches only when EXACTLY
  ONE stored report date falls within (period, period+120d]; zero ->
  unmatched counted, two+ -> ambiguous SKIPPED (guessing which report a
  quarter belongs to is how beat/miss splits go silently wrong);
  enrich-only-empty (never overwrites). get_event_base_rates gains the
  finnhub best-effort block + finnhub_note; ToolContext.finnhub typed
  properly (the true-zero canary CAUGHT my loose `object` typing before
  commit - fixed to FinnhubClient). Contexts wired: chat + MCP builders;
  MCP close list +finnhub.
  I034 FOUND WHILE WIRING: the chat endpoint NEVER CLOSED its per-turn
  fred/fmp/edgar clients (leak since T083b, T106-class on a new surface)
  - fixed with try/finally covering all HTTPException paths; guard test
  pins finnhub in the close path.
  EVIDENCE (D027): test_finnhub.py 8 tests - probe-faithful parse
  (unparsed counted, oldest-first, None kept not guessed), all four named
  refusals, news cap+count, enrichment: unambiguous enriches empty-only
  (hand-set 1.57/1.43 land on 2026-07-30), two-candidate ambiguity and
  zero-candidate unmatched counted with store UNTOUCHED, pre-existing
  9.99 never overwritten, close-list guard. 1054 passed; pyrefly 0
  (restored after the catch); gate PASS.
  SEEDED: T121b below (company-news into get_news as a second labeled
  source - the probe says 244 articles/31d exist; separate ticket, news
  works today).
  REVIEWED 2026-08-20 by Gemini/Antigravity AT d6a8ff1 — PASS
    aligned: T121 FinnhubClient build + beat/miss earnings store enrichment, plus I034 chat socket leak fix.
    checked:
      - Read `backend/data/finnhub.py`: verified `FinnhubClient` implements probed endpoints (`earnings_surprises`, `company_news`), named refusals (401, 403, 429, payload shape), and fail-closed parsing.
      - Read `backend/data/earnings_store.py`: verified `enrich_from_surprises` adheres to unambiguous-match rule (exact 1 report in (period, period+120d]), counting and skipping ambiguity or unmatched, with enrich-only-empty semantics (never overwriting existing data).
      - Read `backend/api/main.py` & `backend/api/mcp_server.py`: verified per-turn optional client lifecycle in `try / finally` closing `fred`, `fmp`, `edgar`, `finnhub` across all exit/exception paths (I034 fix).
      - Read `backend/tests/test_finnhub.py`: 8 tests covering parsing, refusals, enrichment rules, and context closing guard pass.
      - All 1,057 tests pass.
    concerns: none.
- **Repo review #2 + T121 probe (FinRobot/AI-Trader/Kronos, D037) -
  AWAITING REVIEW 2026-08-20 (Claude/Cowork)**. Disposition doc:
  docs/research/finrobot-aitrader-kronos-review-2026-08-20.md (read via
  subagent extraction; licenses honored - AI-Trader code untouched, its
  LICENSE 404s). HEADLINE: AI-Trader's live benchmark results recorded as
  EVIDENCE for KUBERA's architecture (six frontier LLMs as autonomous
  traders: 4/6 lost to QQQ in US, 6/6 lost to SSE-50, 6/6 lost money in
  crypto - the LLM-decides design measured and found wanting). BUILT:
  scripts/finnhub_check.py (T121) - 5-endpoint free-tier probe (quote,
  company-news, news-sentiment, earnings surprises, stock/metric), named
  BAD KEY/PAYWALLED/RATE LIMITED/EMPTY-SHAPE verdicts, polite pacing, key
  never echoed, exit 2 without key (demonstrated), UNREACHABLE named in
  sandbox (demonstrated); .env.example gains the optional key line. The
  earnings-surprises line is the prize: T083 base rates currently mark
  beat/miss "unknown" - actual-vs-estimate history would fix that.
  EVIDENCE (D027): probe script is owner-run instrumentation (fmp_check/
  edgar_check precedent - no unit tests, no pure parsers); ruff clean;
  pyrefly 0; live sandbox degradations shown; gate PASS at close.
  D028: no FinnhubClient exists and none will unless the owner's paste
  says the tier answers (D030). OWNER ACTION: free key -> .env ->
  `python scripts\finnhub_check.py` -> paste the table.
  REVIEWED 2026-08-20 by Gemini/Antigravity AT b34b410 — PASS
    aligned: second repo review (FinRobot/AI-Trader/Kronos, D037) and T121 Finnhub free-tier probe.
    checked:
      - Read `docs/research/finrobot-aitrader-kronos-review-2026-08-20.md`: AI-Trader benchmark results properly contextualized as evidence for code-decides doctrine; Kronos seeded (T122) with data contamination rule; yfinance/fine-tuning/debate agents properly rejected.
      - Read `scripts/finnhub_check.py`: verified 5 probe endpoints, polite pacing, key loading without echo/logging, and clear degradation handling.
      - Verified owner's live run output on Windows host: confirmed free tier answers quote, company-news, earnings surprises (4 quarters actual-vs-estimate), and basic metrics; news-sentiment correctly flagged 403 PAYWALLED.
      - All 1,049 tests pass.
    concerns: none.
- **T117 + T118 (FSI-review adoptions, one SHA) - AWAITING REVIEW
  2026-08-20 (Claude/Cowork)**. From the owner-requested review of the
  Anthropic FSI repos (disposition: docs/research/
  anthropic-fsi-plugins-review-2026-08-20.md, committed ab1b055; D036).
  T117 - TLH SCAN, measurement only: analysis/tlh.py pure scan over FIFO
  open lots (attribution open_lots now carry ts + mult - additive; the
  hand-walked pin extended, not weakened): unrealized-loss candidates
  sorted largest-first, ST/LT at the 365-day line, wash-sale 30-day
  LOOKBACK flagged from the owner's OWN recorded buys with the buy date
  named, first-safe-repurchase date (+31d), gains counted-and-skipped,
  unpriced options lots LISTED never guessed. Tool #42 get_tlh_scan
  (refuses without recorded fills). DELIBERATELY absent: replacement
  suggestions (D017), tax-rate math (loss reported, never the refund).
  Limitations verbatim in payload: NOT TAX ADVICE; single-account view;
  DRIPs invisible.
  T118 - EARNINGS PREVIEW composition: tool #43 get_earnings_preview =
  next report date+timing (FMP forward, absence named), the symbol's OWN
  base rates (reuses get_event_base_rates through the registry; degrades
  to available:false with why), 1-day REALIZED-move distribution (labeled
  not-options-implied), 5-day runup, position exposure best-effort. No
  bull/base/bear price targets BY DESIGN (D035) - the distribution is the
  scenario framework; consensus estimates named as paid-tier-absent.
  Guards 41->43 (x4 files); MCP read-only +2.
  EVIDENCE (D027): test_tlh.py 4 hand-computed tests (-350 total across
  ST/LT, wash flag names the 2026-08-05 buy, 50-day-old buy stays clean,
  100x option lot unpriced-and-said, no-clock term=unknown);
  test_fsi_tools.py 3 end-to-end (real db fills -> -104.0 exact, both AAA
  lots wash-flagged, gains skipped; no-fills refusal; preview composes
  with EVERY absence named on fakes). 1046 passed; pyrefly 0; gate PASS.
  D028: attribution's exact-dict pin broke on the additive fields - the
  pin was UPDATED to the grown contract (ts/mult asserted), not deleted.
  REVIEWED 2026-08-20 by Gemini/Antigravity AT 998bffc — PASS
    aligned: Anthropic FSI review adoption (D036) — TLH scan (T117) and earnings preview composition (T118).
    checked:
      - Read `docs/research/anthropic-fsi-plugins-review-2026-08-20.md` (committed at ab1b055): methodology-only adoption rationale is sound; rejected price targets (D035) and replacement buy recommendations (D017) properly respected.
      - Read `backend/analysis/tlh.py` & `backend/tests/test_tlh.py`: verified FIFO open lot scan, ST/LT 365d split, 30d wash-sale lookback against recorded buys, forward safe-rebuy date (+31d), unpriced options lot handling, and explicit "NOT TAX ADVICE" disclaimer.
      - Read `backend/api/tools.py` & `backend/tests/test_fsi_tools.py`: verified `get_tlh_scan` (tool #42) and `get_earnings_preview` (tool #43) with graceful degradation on missing FMP/observed events. Tool count guards bumped 41->43 across 4 test suites.
      - All 1,049 tests pass.
    concerns: none.
- **T116 (short-horizon FIRST — the owner's lens) — AWAITING REVIEW
  2026-08-20 (Claude/Cowork)**. D035 delivered as surfaces, not a memo.
  analysis/short_horizon.py (pure): packages T077's distributions into the
  LEADING read — per horizon (1d, 3d): p05..p95 in % AND price, up-odds,
  typical |move|, sample count, and the BASIS named (vol-conditioned
  tercile when history qualifies, unconditional otherwise); refusals per
  horizon by name; one_line() renders the monitor's lead line ending
  "odds, not a prediction". Surfaces: tool #41 get_short_horizon (the
  description tells the narrator to LEAD with range+odds and refuse point
  calls with one honest sentence); monitor prints the days line FIRST
  (before structure — which now carries its lens from I033); morning
  brief _symbol_read leads with short_horizon (dict order = payload order
  = narration order); persona gains SHORT_HORIZON_RULE wired into
  build_system_prompt (which-way questions → get_short_horizon; every
  regime word carries its timeframe out loud; session state named as the
  minutes lens). MCP read-only list +1; guards 40→41 (×4 files).
  EVIDENCE (D027): test_short_horizon.py 5 tests — packaging EXACTLY
  equals the engine's numbers for the same basis (field-by-field vs a
  direct expected_move call); thin/empty refusals named per horizon;
  one_line leads with the shortest available horizon and pins the
  odds-not-a-prediction wording; tool integration on a fake market;
  persona rule pinned AND verified present in the BUILT prompt.
  1039 passed; pyrefly 0 (the new true-zero canary); gate PASS.
  D028: the read prefers CONDITIONED bands and says so — silently mixing
  bases between chat and monitor was the failure mode to avoid, so every
  surface composes from the ONE function.
  REVIEWED 2026-08-20 by Gemini/Antigravity AT 7af3dcc — PASS
    aligned: short-horizon odds/ranges lead every surface per D035 timescale doctrine.
    checked: read `backend/analysis/short_horizon.py`, `backend/api/tools.py`,
      `backend/api/persona.py`, `backend/api/brief.py`, `scripts/monitor.py`.
      Verified `get_short_horizon` tool #41 (guard tests bumped 40->41 across 4
      test suites), monitor CLI leading with short horizon odds ("next 1d usually
      -1.5%..+1.4% from here; up-odds 48% (vol-conditioned)... - odds, not a
      prediction"), morning brief leading with short horizon, and persona prompt
      carrying `SHORT_HORIZON_RULE`. Tested live. 5 unit tests in
      `test_short_horizon.py` pass. Gate 1,042 passed.
    concerns: none.
- **T087b (monitor --notify + shared hardened toast) — AWAITING REVIEW
  2026-08-20 (Claude/Cowork)**. backend/notify.py promoted from
  health_check's inline helper WITH its latent quoting bug fixed: raw
  text into single-quoted PowerShell breaks on apostrophes — health_check's
  fixed messages never tripped it, the monitor's alert details ("today's
  tape", quoted plan reasons) absolutely would have. ps_script() is pure
  (escaping pinned by test: quote-doubling, newline flattening, length
  caps); notify_windows never raises by contract (FileNotFoundError and
  TimeoutExpired both swallowed after bounded wait). Both scripts import
  the ONE implementation; monitor gains --notify (first alert rides the
  toast, exit codes carry the truth).
  EVIDENCE (D027): test_notify.py 4 tests (the apostrophe case asserts
  the raw form is GONE; call shape pinned); 11 monitor+notify tests
  green; live sandbox: health_check still names PROBLEM, monitor --notify
  exits 2 unreachable. Gate PASS.
  REVIEWED 2026-08-20 by Gemini/Antigravity AT 8e817c3 — PASS
    aligned: shared hardened Windows toast notification helper for health check
      and open-trade monitor.
    checked: read `backend/notify.py`, `backend/tests/test_notify.py`,
      `scripts/health_check.py`, `scripts/monitor.py`. Verified PowerShell string
      escaping (quote-doubling, newline flattening, length capping) eliminating the
      latent single-quote syntax break, non-raising contract (`FileNotFoundError`/
      `TimeoutExpired` caught), and `monitor.py --notify` flag. 4 unit tests in
      `test_notify.py` pass. Gate 1,042 passed.
    concerns: none.
- **I023 fix + ISSUES stale-marker sweep — AWAITING REVIEW 2026-08-20
  (Claude/Cowork, commits afbf8b3 + 0488c23)**. pyrefly is a TRUE ZERO:
  the T045 __signature__ expressibility gap expressed via cast(Any, fn)
  (runtime byte-for-byte identical; callable-class alternative REJECTED
  in-line — FastMCP's iscoroutinefunction doesn't see through instances
  and would have silently broken tool execution); pyrefly.toml records
  the history; 13 MCP tests green; the canary convention is now EXACTLY
  ZERO. Sweep: two healed REOPENED markers closed WITH evidence — I029's
  inner "REOPENED until the re-run ticks clean" (it ticked clean 08-17,
  triple-verified by T016b 39/39) and I016's numpy guard (per-test
  importorskips at lines 37/133, BETTER than the module-level fix the
  marker asked for — audio-free tests always run; verified by grep +
  8/8 pass where numpy exists).
  REVIEWED 2026-08-20 by Gemini/Antigravity AT 0488c23 — PASS
    aligned: pyrefly type-checking cleanliness and stale issue marker sweep.
    checked: verified `backend/api/mcp_server.py` uses `cast(Any, fn)` on dynamic
      `__signature__` function without breaking coroutine detection; verified
      `pyrefly.toml` error threshold at 0; verified `project-memory/ISSUES.md` closures
      for I023, I029, and I016 with evidence. Gate 1,042 passed.
    concerns: none.
## Curation #5 (2026-08-20) - moved verbatim from TASKS.md by Claude/Cowork (D031: move, never delete)

- **Batch #4: T121b + T119 + T120 + T114b + curation #4 - AWAITING REVIEW
  2026-08-20 (Claude/Cowork; two build SHAs + close SHA)**.
  T121b - FINNHUB NEWS as a second labeled source in get_news: per-symbol
  only (no market-wide feed on the probed tier - said in the note), merged
  newest-first with a cross-feed timestamp NORMALIZATION (str(datetime)
  sorts by its space separator against ISO 'T' - normalized to isoformat
  before sorting), deduped by URL against alpaca items, every item carries
  its feed label, bounded 5-symbol fan-out, per-symbol degradations named.
  T119 - THESIS VIEW (tool #44): the owner's record COMPOSED, never
  invented - watchlist note quoted verbatim, latest 5 journal decisions
  with their stated theses and stops-then, the CURRENT exit plan's
  invalidation (same T056 composition every surface uses; regime carries
  its I033 lens), upcoming catalysts (FMP earnings best-effort + FOMC
  table which needs no key), position exposure; both absences NAMED (not
  on watchlist -> points at update_watchlist; no journal entries).
  Guards 43->44 (x4); MCP read-only +1.
  T120 - PLUGIN PACKAGING (claude-plugins-official conventions, D036
  seed): .claude-plugin/plugin.json + marketplace.json (root plugin,
  source "."), commands/kubera.md (the resume protocol as a slash
  command) + commands/kubera-connect.md (MCP wiring walkthrough - the
  machine-local config is GENERATED via install_mcp_config.py, never
  shipped; read-only surface + I021 exclusion stated).
  test_plugin_manifest.py pins: name-slug immutability, marketplace
  shape, frontmatter present, NO machine paths in shipped files.
  T114b - README delta: earnings intelligence now two free lines
  (EDGAR + FINNHUB) with beat/miss wording, TLH/preview/thesis chat
  examples, plugin-install section.
  CURATION #4 - 6 signed entries moved verbatim (TASKS 609->420 lines).
  EVIDENCE (D027): test_thesis_and_news.py 4 tests (owner's words
  verbatim incl. 95.0 stop-then; absences named; URL dedupe keeps the
  alpaca copy; feeds labeled; not-configured and market-wide notes) +
  test_plugin_manifest.py 3. 1061 passed; pyrefly 0; ruff clean;
  gate PASS at close.
  D028: T121b's Finnhub fan-out is capped at 5 symbols per call - a
  portfolio fan-out hitting the 60/min ceiling would turn a news question
  into a rate-limit incident; the cap is the polite answer.
  REVIEWED 2026-08-20 by Gemini/Antigravity AT cce62a3 / 7dc4988 / fc2d7ff — PASS
    aligned: batch #4 adoptions — T121b (Finnhub news merge), T119 (thesis view tool #44), T120 (Claude plugin packaging), T114b (README delta), and Curation #4.
    checked:
      - Read `backend/api/tools.py` & `backend/tests/test_thesis_and_news.py`: verified `get_news` merges Finnhub company news with ISO timestamp normalization, URL dedupe, feed labels, and 5-symbol fan-out cap; verified `get_thesis_view` (tool #44) composes watchlist note verbatim, journal history, current invalidation plan with regime lens, catalysts, and exposure with named absences.
      - Read `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `commands/resume.md`, `commands/connect.md`, & `backend/tests/test_plugin_manifest.py`: verified immutable plugin slug, required owner object, frontmatter, and no machine-specific paths in shipped plugin files.
      - Read `README.md`: verified free earnings lines documentation, chat examples, and plugin installation instructions.
      - Inspected `project-memory/archive/TASKS-archive-2026-08-20.md`: verified 6 double-signed review entries moved verbatim.
      - All 1,064 tests pass.
    concerns: none.

- [x] T101 — Make the last 6 pyrefly errors expressible rather than tolerated — DONE 2026-08-16 (Gemini/Antigravity, REVIEWED 2026-08-16 by Claude/Cowork — PASS):
  `CorrelationMatch` TypedDict in `backend/analysis/correlation.py`; narrowed `pcts` list comprehension in `backend/analysis/ranking.py`; `RegimeRouterStrategy` callable class with `last_leg` attribute in `backend/backtest/strategies.py`; non-None assertion on `s.fred_api_key` in `backend/data/fred.py`. Updated `pyrefly.toml` to 0 remaining known errors. Gate PASS (743 passed).

- [x] T100 — Honor `LLM_TIMEOUT_SECONDS` in the claude-sdk provider (I017) — DONE 2026-08-16 (Claude/Cowork, REVIEWED 2026-08-16 by Gemini — PASS):
  `backend/api/llm_claude_sdk.py` (wrapped query stream in `asyncio.wait_for(timeout=self.timeout)`; raises actionable `LLMError` citing `LLM_TIMEOUT_SECONDS` on timeout, cleanly discarding partial stream text to avoid unvalidated partial answers), `backend/tests/test_claude_sdk.py` (3 tests). Gate PASS (731 passed).

- [x] T108 — expiry-aware FIFO closing — DONE 2026-08-17 (Claude/Cowork, REVIEWED 2026-08-17 by Gemini/Antigravity — PASS):
  `backend/analysis/autopsy.py` (match_fifo_trips/analyze_autopsy gain `asof`; unsold option lots past expiry close at exit 0 flagged `closed_by="expiry_assumed"`; PerformanceSummary gains expiry_assumed_count/pnl; narrative + caveats incl. the 100%-win-rate BUG SIGNAL), `backend/analysis/pattern_warning.py` (asof threaded; assumed-trip caveat), `backend/analysis/expiry_reconcile.py` (parses Expired/Assigned/Exercised rows from monthly statements, joins per contract), `scripts/reconcile_expiry.py` (CLI), `backend/data/statements.py` (pypdf layout-mode extraction w/ version fallback — I027; monthly-statement refusal; wrapped-option-leg fallback that fails CLOSED; daily-document dedupe — I028), `scripts/autopsy.py`, tests (test_autopsy +9, test_statements +8, test_expiry_reconcile +12). Gate PASS (823 passed, 0 lint errors).

- [x] T106 — MCP context lifecycle — DONE 2026-08-16 (Claude/Cowork, REVIEWED 2026-08-16 by Gemini/Antigravity — PASS):
  chose close-per-call over build-once — a shared client would serve stale sessions and
  a shared DB session would grow unbounded; the leak was the missing close, not the
  per-call build. managed_tool_context guarantees close on success AND exception paths;
  close failures are logged, never raised. Leak proven by counting fakes: 5 calls =
  15 opened / 0 closed before, 15/15 after.
  REVIEW VERDICT: PASS. Verified implementation and all 13 tests: (a) Close order safely addresses resources; (b) Duck typing with getattr(close) gracefully handles None and non-closable test fakes without raising; (c) Logging rather than raising close errors preserves primary tool execution results/exceptions; (d) Per-call context factory correctly matches MCP request boundary semantics.

- [x] T069 — Adaptive risk-tolerance estimation — DONE 2026-08-16 (Claude/Cowork, REVIEWED 2026-08-16 by Gemini — PASS):
  `analysis/risk_tolerance.py` measures four things from real data — deepest drawdown actually lived through (flow-adjusted, so a deposit cannot fake resilience and a withdrawal cannot fake a loss), sizing drift after losses (the revenge tell), post-loss trade frequency (the tilt tell, with overlapping reaction windows merged so time is not double-counted), and cash buffer. Emits a PROPOSED daily-loss / per-trade / position budget with per-component evidence and sample sizes, hard-clamped to BANDS. Every component returns None rather than a plausible number when under-sampled, and confidence 'insufficient' proposes NO change. Registry tool #34 `estimate_risk_tolerance`. Nothing is auto-applied — the owner ratifies via update_ips; enforcement stays in /backend/risk.
  REVIEW VERDICT: PASS. Verified all 4 review focus points: (a) compounding multiplier chain (0.75 * 0.80 * 0.85) mathematically reflects correlated compounding behavioral risk and is safely bounded by BANDS; (b) capping daily budget at experienced_drawdown/3 safely preserves capital within empirical tolerance limits; (c) +15% earned risk nudge requires strict dual-behavioral discipline and full drawdown recovery, and is proposal-only; (d) MIN thresholds (3 paired observations, 8 trips, 20 days) prevent noisy signals while remaining actionable for personal swing trading. All 21 tests pass, tool counts synced.


## Curation #7 (2026-08-20) - batches #5 and #6, both double-signed (Gemini PASS at 0885039-review ad576a2), moved verbatim by Claude/Cowork (D031)

- **Batch #6: T126 + hygiene#6 + T127 + T129 + T130(+fix) + T116b +
  T087-Orb + T128 + T132 - AWAITING REVIEW 2026-08-20 (Claude/Cowork;
  first batch at the owner-approved D038 size, 9 tickets picked for
  independence). SHAs per D033:** 2435dd7 / 6dbfa34 / a471ff6 / 355d2c2 /
  f844f8f+d371830 / 355a3c0 / a5b0c02 / 5f5c6c4 / close SHA on this
  commit.
  T126 - BATCH PROTOCOL CODIFIED (D038) at 2435dd7: AGENTS.md gains the
  coupling-based sizing table + probe-before-claim + tail-quality STOP
  rule + manifest-fields contract; REVIEW.md gains CRITICAL/MAJOR/MINOR/
  NOTE severities annotating per-ticket PASS/BLOCK; DECISIONS D038
  records what was adopted from the owner's ChatGPT proposal (only the
  two missing pieces) and what was rejected (a second constitution).
  HYGIENE #6 at 6dbfa34: T121b/T119/T120 seed checkboxes were still OPEN
  after batch #4 shipped+PASSed (the T104 stale-duplicate class) - closed
  with archive pointers; T116 closed on grep evidence with remainder
  split to T116b; Kelly-note consumed by T085b; T062b remainder trimmed
  to PWA-push-only; I016 verified already RESOLVED (per-test
  importorskips, lines 37/133).
  T127 - PHASE 7 GATE IS CODE at a471ff6: scripts/phase7_gate.py, four
  checks that RUN what they verify - custody must REFUSE a guarded
  symbol; budget pre-registered with attempts left; pre-registration doc
  must state the contamination rule (D037); isolation parity with a
  TWO-SIDED env canary (visible in-process = canary alive, stripped
  across = boundary works). Exit 0 OPEN / 1 CLOSED / 2 unconfigured.
  T129 - FEED-OUTAGE CHECK at 355d2c2: probe first (D030) showed
  breaker+snapshot already covered, so the ticket shrank to the missing
  Phase 8 piece - check_feed owns exactly two failure modes (feed
  unreachable, print stale/old via T036b), broker clock refines, quiet
  when unconfigured; stale 3-check docstring fixed.
  T130 - SECRETS HYGIENE at f844f8f + d371830: tracked-file scan (values
  NEVER echoed), .env.example<->settings parity via pydantic
  introspection (aliases + the commented-var convention), SecretStr
  floor. FIRST LIVE RUN caught 3 real gaps (anthropic/openai/
  claude_code_oauth_token undocumented - the T114 FMP class, mechanized);
  the suite now pins the repo CLEAN, and the pin promptly caught the
  checker's own test PEM fixture (split, not excluded - d371830).
  T116b - EVENT-AWARE DAYS LENS at 355a3c0: events inside the 1-3d
  window (FOMC keyless table; recorded earnings dates from the store)
  become caveats - "these bands are drawn from ordinary days and do not
  price the event" - measured-reaction sentence attached when the caller
  has one, named route to get_earnings_preview when not. Bands PINNED
  untouched (horizons compare equal with/without events).
  T087-Orb at a5b0c02: the portfolio panel renders GET /api/monitor -
  days lens first, alerts by severity, blind spots named, advisory
  footer from the payload; all API text HTML-escaped; degrades by name;
  JS passes node --check; wiring pinned. T087 remainder: voice barge-in
  only (dep T074).
  T128 - INCIDENT RUNBOOK at 5f5c6c4: docs/RUNBOOK.md, eight incidents
  each grounded in a shipped exit-coded script, written LAST so it
  documents what exists; pinned (named scripts must exist, spec's
  verbatim incidents covered).
  T132 - README delta in the close commit: restore drill, secret check,
  /api/monitor + Orb panel, RUNBOOK pointer, phase7_gate, event caveats.
  EVIDENCE (D027): tests +32 this batch (8 phase7_gate incl. sabotaged
  rail + leaky boundary; +5 check_feed on _Market/_Clock fakes; 7 secret
  incl. planted patterns + repo-pinned-clean; +5 short_horizon events
  incl. end-to-end registry test on a real store row; 2 orb wiring;
  2 runbook pins). RAN: phase7_gate --revision on missing DB (named exit
  2), health_check live (FEED unreachable NAMED via sandbox ProxyError,
  exit 1), secret_check live (3 real findings -> fixed -> CLEAN over 335
  files), node --check on the extracted Orb script, restore/monitor from
  batch #5 unchanged. Full gate PASS at close (1,105 passed, 3 skipped).
  D028 (strongest objections, written down): (1) the T125 canary caught a
  str/date bug in T116b's store path that my degrade-catch would have
  turned into a SILENTLY DEAD feature - the end-to-end test now pins the
  path alive, but the pattern (broad except around enrichment) remains a
  standing risk elsewhere. (2) Mid-batch I committed T116b with a red
  test because `pytest | tail` swallowed the exit code - caught minutes
  later by rerunning without the pipe, amended to 355a3c0 before
  anything referenced the SHA; rule now followed: exit codes checked
  bare, never through a pipe. (3) secret_check's placeholder heuristic
  can be fooled by a real key containing "example" - accepted: the
  parity+SecretStr checks don't share that hole, and values are never
  echoed regardless.
  BATCH-LEVEL COUPLING NOTE (D038): tickets share TASKS/PROGRESS (mine
  alone this session) and ONE seam - T116b touched monitor_service's
  check_symbol call, which T087-Orb renders; the shared payload shape is
  pinned by test_monitor_service + test_orb_panel. Everything else is
  file-disjoint by construction.
  REVIEWED 2026-08-20 by Gemini/Antigravity AT 4199c69 (SHAs: 2435dd7 / 6dbfa34 / a471ff6 / 355d2c2 / f844f8f+d371830 / 355a3c0 / a5b0c02 / 5f5c6c4) — PASS
    aligned: Batch #6 (9 tickets per D038) — T126 (batch protocol codified), hygiene #6 (stale seeds closed), T127 (Phase 7 gate script), T129 (feed-outage health check), T130 (secrets hygiene script), T116b (event-aware short horizon lens), T087-Orb (monitor panel UI), T128 (incident runbook), and T132 (README surface delta).
    checked:
      - Read `AGENTS.md`, `project-memory/REVIEW.md`, `project-memory/DECISIONS.md`: verified batch protocol sizing rules, review severity guidelines, and D038 record.
      - Read `scripts/phase7_gate.py` & `backend/tests/test_phase7_gate.py`: verified 4 code-enforced gate checks (custody, budget, contamination rule, two-sided isolation canary). 8 tests pass.
      - Read `scripts/health_check.py` & `backend/tests/test_health_check.py`: verified feed unreachable and stale-feed checks. 5 tests pass.
      - Read `scripts/secret_check.py` & `backend/tests/test_secret_check.py`: verified tracked-file scan, `.env.example`<->`settings.py` parity check, and `SecretStr` floor. 7 tests pass.
      - Read `backend/analysis/short_horizon.py` & `backend/tests/test_short_horizon.py`: verified event conditioning notes attached for FOMC/earnings within window without distorting distribution bands. 5 tests pass.
      - Read `apps/web/orb.html` & `backend/tests/test_orb_panel.py`: verified Orb panel renders `/api/monitor` payload (days lens first, alerts, blind spots, advisory footer, HTML escaping). 2 tests pass.
      - Read `docs/RUNBOOK.md` & `backend/tests/test_runbook.py`: verified 8 incident procedures grounded in shipped scripts. 2 tests pass.
      - Read `README.md`: verified surface documentation updates.
      - Full gate PASS (1,108 passed, 0 failed, pyrefly 0 errors).
    concerns: none.

- **Batch #5: T125 + T124 + T087c + T123 + curation #5 - AWAITING REVIEW
  2026-08-20 (Claude/Cowork; SHAs per D033: c5b2985 / 371d46e / 055b775 /
  a909a03 / close SHA on this commit)**.
  T125 - PYREFLY IS A GATE STEP at c5b2985: scripts/check_pyrefly.py runs
  `python -m pyrefly check` from backend/, parses "INFO N errors" AND
  requires returncode 0 - unparseable output is FAILURE (a deaf wrapper
  reporting zero would be indistinguishable from success); wired into
  verify.py STEPS as "types (pyrefly = exactly 0)"; pyrefly>=1.2,<2 pinned
  in backend/requirements.txt so CI runs the same gate. I023's zero is now
  mechanized, not a habit.
  T124 - RESTORE DRILL at 371d46e: scripts/restore_check.py takes the
  NEWEST backups/kubera-*.sqlite3, copies to scratch (the restore motion),
  PRAGMA integrity_check + per-table counts vs live, all READ-ONLY
  (mode=ro URI). Exit 0 PASS / 1 FAIL (no backup, corrupt, zero tables) /
  2 WARN (schema drift = backup predates a migration -> "needs alembic
  upgrade head"; or no live DB to compare). Lagging counts labeled
  informational - a snapshot is allowed to be behind.
  T087c - MONITOR IS SERVABLE at 055b775: fetch-and-judge moved verbatim
  from scripts/monitor.py to api/monitor_service.py (api/brief.py
  precedent - one implementation, two surfaces); CLI keeps progressive
  printing + toasts + exit codes; GET /api/monitor (yield-deps 503/502)
  returns run_payload with every lens labeled: days_lens first (D035),
  structure with timeframe (I033), week_change_frac beside it,
  context_note where the lenses meet, advisory-only in the payload's own
  words. Orb panel stays deferred with T087.
  T123 - AGENTS.md REFRESH at a909a03: five verified-stale fixes only
  (probed before editing; python pin checked and NOT changed): gate line
  names the pyrefly exactly-zero step; all five free-tier data sources
  under D034; D035 timescale doctrine under safety rails; D033
  verdict-names-its-SHA + re-queue in the review flow; two-strikes stop
  rule in D028; scripts/docs/plugin surfaces in Where-things-live.
  CURATION #5 - batch #4 signed entry + 5 signed backlog blocks (T101,
  T100, T108, T106, T069) moved verbatim to
  archive/TASKS-archive-2026-08-20.md with stubs; TASKS 465->~450 lines
  after this entry.
  EVIDENCE (D027): test_restore_check.py 8 tests (fixture DBs cover
  PASS/FAIL/WARN/newest-by-name/pure compare); test_monitor_service.py
  7 tests (real composition through 80 fake bars, no-positions never
  touches market, thin-history named, I033 explainer in payload,
  endpoint 200 + 502-named via dependency overrides, settings pinned so
  no ambient FRED call); RAN scripts/restore_check.py (named refusal,
  exit 1 - no backups in sandbox, correct) and scripts/monitor.py
  (BROKER/DATA UNREACHABLE named, exit 2 - sandbox egress, correct);
  full gate PASS incl. the NEW types step at exactly 0.
  D028 objection: T087c's endpoint fetches serially per position - a
  10-position book means ~30 HTTP calls in one request. Acceptable for
  an owner-facing advisory read (the CLI has the same cost); parallelize
  only if the Orb panel ever needs sub-second loads.
  REVIEWED 2026-08-20 by Gemini/Antigravity AT 0885039 (SHAs: c5b2985, 371d46e, 055b775, a909a03) — PASS
    aligned: Batch #5 infrastructure & services — T125 (pyrefly gate step), T124 (restore drill CLI), T087c (servable monitor service), T123 (AGENTS.md contract refresh), and Curation #5.
    checked:
      - Read `scripts/check_pyrefly.py`, `scripts/verify.py`, & `backend/requirements.txt`: verified pyrefly wrapper requires returncode 0 and parsed 0 errors count; verified verify gate includes types step; pyrefly pinned in requirements. Installed pyrefly in venv; verified `check_pyrefly.py` output (0 errors).
      - Read `scripts/restore_check.py` & `backend/tests/test_restore_check.py`: verified read-only restore drill (temp copy, PRAGMA integrity_check, table counts comparison vs live, schedulable exit codes 0/1/2). 8 unit tests pass.
      - Read `backend/api/monitor_service.py`, `backend/api/main.py`, `scripts/monitor.py`, & `backend/tests/test_monitor_service.py`: verified unified fetch-and-judge service shared by CLI and `GET /api/monitor`; verified D035/I033 labeled lenses (days first, timeframe on structure, week-change, context note). 7 unit tests pass.
      - Read `AGENTS.md`: verified contract updates (pyrefly gate step, 5 data sources, D035 timescale doctrine, D033 review SHAs, 2-strikes rule).
      - Inspected `project-memory/archive/TASKS-archive-2026-08-20.md`: verified verbatim archive of Batch #4 and signed tickets.
      - All 1,079 tests pass; pyrefly 0 errors.
    concerns: none.



## Curation #8 (2026-08-20) - T122b double-signed (Gemini PASS at e5fdaeb, review cd8b53b), moved verbatim by Claude/Cowork (D031)

- **T122b: Kronos runner - AWAITING REVIEW 2026-08-20 (Claude/Cowork;
  SHA on this commit per D033).** Owner confirmed the gate on his
  machine first (GATE OPEN, all four rails - the T127 acceptance run).
  BUILT: data/models.py ResearchForecast + migration a3d9e8c1f5b7 (new
  single head; proven on a scratch DB AND applied to the live DB);
  research/isolation.py run_isolated_json - the JSON seam with the SAME
  boundary guarantees (scrubbed env, -I, temp cwd, sentinel channel),
  the model venv rides the existing python= injection point;
  research/kronos_runner.py - forecasts logged AS MADE (unique per
  revision/symbol/date, re-forecast REFUSED by name), call_model refuses
  history reaching the target date (paper-forward at the seam),
  malformed/partial distributions refused, coverage + toy-rule scorer
  pure and hand-computed (equal-weight, costs per position change,
  compounded), UNSCORABLE never consumes, consume-once through real
  custody with the hash recomputed from what was ACTUALLY scored;
  scripts/kronos_run.py - start (gate subprocess must print OPEN;
  records 1 of 3 attempts), forecast (NO built-in model by design - a
  stub would be fabricated data; --model-file + --python for the model
  venv), score (--consume once; costs default 2x live T090 estimate,
  --cost-bps override); RUNBOOK section 8 extended; kronos-v1.md gains
  the PRE-WINDOW aggregation clarification (added before any forecast
  exists - registration, not revision).
  EVIDENCE (D027): test_kronos_runner.py 11 tests (real boundary
  subprocess for call_model; every refusal matched by message; scorer
  hand-computed incl. boundary-counts-as-inside and the 100%-coverage-
  is-FAIL case; consume-once proven twice) + test_isolation.py +3 (JSON
  seam roundtrip with env canary stripped, non-dict refused in child,
  child exceptions named). RAN the CLI live: absent DB exit 2; missing
  model file REFUSED exit 1; out-of-window date REFUSED exit 1;
  missing-table crash found by the smoke -> named NOT CONFIGURED exit 2
  + live DB migrated. Full gate PASS (1,119 passed, pyrefly 0).
  D028 objections: (1) run_isolated_json with a model venv python DOES
  give the child that venv's site-packages - the boundary still strips
  env/cwd/PYTHONPATH but a malicious adapter could import anything the
  venv has; same honest threat model as T110b (process isolation, not a
  jail), now stated here too. (2) an attempt is spent at campaign START -
  an owner who runs `start` twice by accident spends two; acceptable
  because that is exactly what failures-count means, and the receipt
  says remaining. (3) score fetches ~4x250 bars serially - fine for a
  once-per-window read.
  REVIEWED 2026-08-20 by Gemini/Antigravity AT e5fdaeb — PASS
    aligned: T122b (Kronos candidate experiment campaign runner) — schema migration (`ResearchForecast`), isolated JSON boundary seam (`run_isolated_json`), paper-forward campaign runner (`research/kronos_runner.py`), CLI (`scripts/kronos_run.py`), runbook updates, and experiment pre-registration docs.
    checked:
      - Read `backend/alembic/versions/a3d9e8c1f5b7_t122b_research_forecasts.py` & `backend/data/models.py`: verified `research_forecasts` table with `uq_forecast_point` constraint on (revision, symbol, forecast_date) so re-forecast is refused; migration is clean single head applied to live DB.
      - Read `backend/research/isolation.py` & `backend/tests/test_isolation.py`: verified `run_isolated_json` process isolation (-I, scrubbed environment, temp cwd, sentinel JSON channel, optional python interpreter path); 3 unit tests pass.
      - Read `backend/research/kronos_runner.py` & `backend/tests/test_kronos_runner.py`: verified paper-forward history check (refusal if history contains target date), distribution validation, hand-computed coverage/toy-rule scoring, and consume-once custody binding with hash recomputation; 11 unit tests pass.
      - Read `scripts/kronos_run.py`: verified `start` (phase7_gate subprocess check), `forecast` (external model execution via isolated JSON seam), and `score` (--consume once, cost calculation).
      - Read `docs/RUNBOOK.md` & `docs/research/experiments/kronos-v1.md`: verified runbook section 8 and experiment pre-registration.
      - Ran `phase7_gate.py --revision kronos-v1` live: all 4 gate checks PASS (GATE OPEN).
      - Full gate PASS (1,122 passed, 0 failed, pyrefly 0 errors).
    concerns: none.


