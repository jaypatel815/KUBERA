# ISSUES

Known bugs and gotchas, so no agent re-diagnoses one from scratch. Format per PROJECT_SPEC.md §11.
Close entries by moving them to the bottom under "Resolved" with the fix commit.

## Open
- I031 [DEFECT DISCOVERED 2026-08-19 during T076b review] `analysis/fomc.py`
  transcribed the June 2027 FOMC decision date as `2027-06-16`. The Federal
  Reserve's published calendar (federalreserve.gov/monetarypolicy/fomccalendars.htm
  anchor #45694) shows the June 2027 meeting is June 8-9* (decision day June 9,
  `2027-06-09`). The code date is off by a full week, leaving the real June 2027
  meeting unguarded. Fix: update the entry in `FOMC_DECISION_DATES` to `2027-06-09`.
- I029 [ROOT-CAUSED AND FIXED 2026-08-17 against the owner's March probe —
  awaiting his clean re-reconcile to close. What the OBSERVED rows showed,
  correcting both of my hypotheses:
  1. DATES: the underlying dates were RIGHT. Two real defects instead:
     (a) the reconcile printout displayed UTC, so a 3:08 PM trade read as
     19:08:01 and two placeholder rows read as 05:00:00 "trades"; and (b) on
     rows ...055213/...468374 Schwab's `tradeDate` degrades to a DATE-ONLY
     placeholder (midnight ET) while `time` carries real execution — the
     mapper preferred the wrong field. FIXED: mapper prefers `time`
     (regression test from the observed row); reconcile prints Eastern with
     the zone labeled.
  2. EXPIRATIONS: the API emits NO transaction row at all for a worthless
     expiry — nothing was fabricated; the events are simply ABSENT from this
     endpoint (observed: 660P x10, 656C x3, 170C x3 all invisible). FIXED:
     reconcile now prints an EXPECTED EXPIRATIONS section (open option lots
     past expiry -> "expired worthless, $0, no Schwab transaction exists")
     so the tick-off matches the statement's Expired rows; T108's $0 closing
     REMAINS the authoritative treatment (there is nothing to "observe" in
     this feed — my expiry_observed idea was wrong for this endpoint).
  BONUS from the probe: the NVDA 167.5P sale of 2 @ 0.64 (13:55:05Z) is in
  the API — the T108 "not_in_statements" puzzle is resolved; that sale was
  real. ALSO: transferItems carry per-trade COMMISSION/OPT_REG_FEE/TAF_FEE —
  the API has real fee data (statement-parity), which T016c should persist.
  PROCESS NOTE (D028): the probe script itself shipped with 4 pyrefly errors
  because I ran ruff+gate but skipped pyrefly that session; caught and fixed
  this one. Original entry follows:]
  I029 [SCHWAB API MAPPING — found by THE OWNER's reconciliation, 2026-08-17]
  He did the T016 tick-off against his March statement and caught two defects
  the unit tests could never catch, because (as test_schwab.py admits in its
  own docstring) the fixtures follow Schwab's PUBLISHED shapes and "have NOT
  been checked against a live pull":
  1. DATES OFF: imported transaction dates do not match when he actually
     traded. The mapper prefers row["tradeDate"] and falls back to row["time"]
     then settlementDate — the live rows likely carry a posting/settlement
     timestamp where we expect execution time (the same settle-vs-trade class
     as T102's statements and T108b's first cut). RTH trades print the same
     date in UTC and ET, so this is the SOURCE FIELD, not a timezone artifact
     (distinct from T111).
  2. EXPIRATIONS PRESENTED AS SALES: expired contracts appeared in the output
     as if sold — "yes they were 'sold' but I didn't make anything off of it."
     Either Schwab emits expirations as TRADE rows (which _security_leg maps
     as sells, or rejects on a 0/absent price into unmapped), or as an
     unhandled type. Correct target state: an API expiration row becomes an
     EXPIRY event — qty removed at price 0, feeding the T108 pipeline as
     closed_by="expiry_OBSERVED" (stronger than expiry_assumed — the broker
     told us). Never a sale with invented proceeds.
  FIX PATH (T102 discipline — observed rows, not guesses): the owner runs
  scripts/schwab_probe_shape.py (NEW) and pastes the row shapes; the mapper
  is then fixed against reality and re-reconciled. T016's acceptance is
  REOPENED until that re-run ticks clean — which is the reconciliation
  process WORKING, not failing.
- I028 [FIXED 2026-08-17 by T108 dedupe + T108b statement importer (e15a785,
  reviewed BLOCK→PASS) — reconciliation now 13/13 clean, option balance 36/36,
  imported fills carry derived T+1 trade dates with a date_source flag.
  DATA QUALITY — duplicate daily downloads + missing documents]
  (2026-08-17, found by the T108 reconciler, Claude/Cowork)
  Schwab's daily confirmation lists EVERY trade of the day; the owner saved the
  same document once per trade under per-trade filenames. 47 of the 91 PDFs in
  private/statements are re-downloads (24 days saved 2–5x, all with byte-
  different files but IDENTICAL fill-sets) — so "250 fills" was really 83, and
  every behavioural number computed before 2026-08-17 (T103 autopsy, T104
  evidence, the original I026 measurement) was inflated by multi-counted days.
  FIXED in code: `dedupe_daily_documents` collapses identical same-day
  fill-sets, keeps supersets over subsets, and keeps-but-loudly-reports
  overlapping non-nested sets. Duplicates are REPORTED in ParseReport, never
  silent.
  STILL MISSING (reconciler output, owner's statements as ground truth):
  confirmations for SPY 692P x8 (of 9), SPY 660P x8 (of 10 — my first note here
  said x4, a stale pre-dedupe number), SPY 733P x35 (of 135 — the 35 @ $0.1597
  fill is visible in the May statement itself), NVDA 182.5P x2 (Jan 2, before
  coverage begins). Realized losses are therefore still UNDERSTATED. Repair
  path: T108b statement-transaction importer, not manual PDF hunting.
  UPDATE 2026-08-17: owner delivered June + July statements. SPY 735P 06/08
  CONFIRMED (3 expired vs 3 assumed, exact — the "x12" first recorded was
  pre-dedupe). July verified as a genuine no-trading month (text extracted,
  zero transaction rows). Only remaining unexplained item: NVDA 167.5P x2
  assumed-expired with no Expired row in any statement — most likely a missing
  SALE confirmation rather than an expiry; T108b's import will settle it.
- I027 [FIXED 2026-08-17 — parser silently broken by a pypdf version change]
  pypdf 6.13 joins PDF text lines differently from the version the T102 parser
  was built against: every row split ("03/03 Purchase XLE" alone on its line),
  so ALL 86 real confirmations returned "no fill rows matched" — 0 fills, no
  error, in this sandbox. The verify gate stayed green because fixtures are
  .txt. FIX: `extract_pdf_text` uses `extraction_mode="layout"` (preserves the
  column spacing the regexes need) with a TypeError fallback for pypdf < 3.17.
  LESSON: an extraction-dependent parser needs a real-file canary — any run
  that parses the owner's folder to 0 fills should be treated as an
  environment regression, never as "no data". Same class as I018.
- I026 [FIXED 2026-08-17 by T108, pending Gemini review — CRITICAL —
  SURVIVORSHIP BIAS: expired options were invisible to every behavioural
  number] (found by THE OWNER, not by any agent)
  CORRECTION TO THE MEASUREMENT BELOW (2026-08-17): the original numbers were
  computed on I028's multi-counted fills. On deduped data: 13 expiry-assumed
  lots, -$3,961 of confirmations-visible expired premium (not $6,308.57), with
  MORE premium invisible in the 49 statement-side contracts I028 lists. The
  honest headline after T108: 49 trips, -$4,228.17 total realized, 55.1% win
  rate; SPY puts 5W/7L -$3,004. The direction of the original diagnosis was
  right; its magnitude was distorted by the very data bug it sat on top of —
  which is why measurements get re-run after every data fix.
  He asked one question — "you're telling me I've never lost money on SPY
  puts?" — and it broke the whole P&L chain. The FIFO round-trip matcher
  (autopsy, pattern warnings, holding periods, T069 inputs) closes a trip only
  when a SELL fill exists. An option that expires worthless produces NO
  confirmation, so every 100%-loss ride-to-zero simply never becomes a trip.
  Only sold positions — disproportionately winners — enter the record.
  MEASURED on his confirmations: 14 of 28 option contracts carry unsold
  quantity past expiry, ~$6,308.57 of premium with no exit fill. SPY alone:
  8 contracts, ~$4,226 (the 2026-05-11 733P x100 is ~$2,900 of it).
  CONSEQUENCES, all overstated in his favour — the worst direction:
    · "SPY options 19/19 wins +$2,470" (my T104 review evidence) is FALSE as
      a record of his trading; true SPY option net is roughly -$1,756.
    · The autopsy's "+$11,134 realized, 73.4% win rate" excludes up to ~$6,308
      of pure losses; true realized is nearer $4,826 and the win rate is far
      lower once ~14 expired lots count as losing trips.
    · T104's "clear" verdict on a 0DTE SPY put was issued against this biased
      base — precisely the trade class where his losses are hidden.
  WHO MISSED IT: Gemini built the matcher; I reviewed T103 AND T104 against
  the same biased data and called the clear verdict "earned". D028's falsify
  question — "what would make 19/19 wrong?" — had an obvious answer (where are
  the losses?) and I did not ask it. A 100% win rate should itself have been
  treated as an anomaly detector.
  CAVEAT, stated so the fix is honest: unsold-past-expiry can also mean
  exercised/assigned (would show as stock+cash movements) — the monthly
  STATEMENTS can distinguish; for OTM 0DTE puts worthless expiry dominates.
  FIX (T108): expiry-aware trip closing — an option lot whose expiry has
  passed with no sell closes at exit price 0 on the expiry date, flagged
  `closed_by="expiry_assumed"`, reconciled against monthly statements where
  available. Until T108 lands, EVERY win-rate and realized-P&L figure from
  confirmations must carry the caveat that expired options are missing.
- I024 [FIXED 2026-08-16 in 5d22682 — verified by re-running on 250 real fills: minutes/hours buckets now empty, narrative states duration is unrecorded]
  `analysis/autopsy.py:174,216` stamp every dateless fill with `time(12, 0)`.
  Schwab confirmations carry NO time of day (statements.py exposes `trade_date:
  date` because the document prints only a date), so every same-day round trip
  measures as exactly 0.0 days and lands in the "minutes" bucket.
  VERIFIED on the owner's real data: distinct times of day across 250 fills =
  {''}; median_days 0.0; 61 round trips reported in "minutes" with $12,939
  realized. The narrative prints "Median hold is 0.0 hours" as a finding.
  This violates AGENTS.md priority 1 (never present placeholder data as real).
  MY SHARE OF IT: T105 added minutes/hours/same_day buckets without recording
  that statement data cannot populate them. Correct for API fills, impossible
  for confirmations.
  FIX: carry `time_known: bool`; report `unknown` rather than 0.0, and say
  plainly that confirmations do not record time of day.
- I025 [FIXED 2026-08-16 in 5d22682 — segregated by asset class; equity-only comparison now reads 12.53x, N=6. Concern carried: "signature" overstates N=6]
  The tell compares an equity notional against an option premium in one median:
  NOK 1925 shares @ $15.98 = $30,761 against NVDA 1 contract @ $0.05 = $5.
  The resulting "sizing up by 78.05x after losses (N=7)" is a category error
  presented as a psychological finding — the single most consequential line in
  the report, and the one most likely to change how the owner trades.
  FIX: compute drift WITHIN an asset class or on risk-normalised terms, and
  refuse to emit the tell when the two populations are not comparable.
- I023 [OPEN — pyrefly is at 1, the config still claims 0] (2026-08-16)
  T101 drove the checker to zero and wrote "KNOWN REMAINING ERRORS — 0" into
  pyrefly.toml with the instruction "if new errors appear, investigate
  immediately before suppressing". T045 then introduced one:
    backend/api/mcp_server.py:195 — `fn.__signature__ = inspect.Signature(...)`
    Object of class `FunctionType` has no attribute `__signature__`
  It is legal Python (functions accept arbitrary attributes, and CPython honours
  __signature__ for introspection), so this is an expressibility gap rather than
  a defect — but the invariant an agent just established was broken by the next
  ticket, and the config now lies about the count.
  FIX during the T045 v2 review: either express it (a small callable class with a
  real signature, as T101 did for RegimeRouterStrategy) or update the pyrefly.toml
  block to say 1 with the reason. Silently leaving the comment wrong is the one
  option that is not acceptable — it is how the 138-error state started.
- I021 [BLOCKING T045 — the MCP server bypasses the confirmation gate] (2026-08-16)
  DEMONSTRATED, not inferred: through the MCP server, with no confirmation step,
  `update_ips` set max_drawdown_frac=0.99 and objectives="YOLO everything" on a
  live row. Cause: `make_default_tool_context()` hardcodes `confirmed=True`, the
  flag that tools.py:110 explicitly says must never be set from model output.
  Four mutating tools are exposed (update_ips, record_decision, mark_decision,
  update_watchlist) behind a docstring claiming read-only.
  FIX: confirmed=False by default; read-only allowlist as the default
  tool_filter; gated tools only via an explicit opt-in argument.
- I022 [BLOCKING T045 — undeclared AND version-wrong dependency; CI is red]
  `mcp` is in no requirements file and test_mcp_server.py imports it at module
  scope, so a fresh checkout aborts collection — I016/I018 a third time.
  ALSO: `pip install mcp` now resolves to 2.0.0, which has no
  `mcp.server.fastmcp` module; that path only exists on 1.x (verified against
  1.29.0). A fresh machine following the README cannot import the server at all.
  FIX: pin `mcp>=1.29,<2` in a requirements file and guard the test with
  `pytest.importorskip("mcp.server.fastmcp")`.
- I020 [FIXED 2026-08-16 in T105] the Schwab API import would have DROPPED most of the owner's trading
  FOUND by parsing his real confirmations (T102). His book is not what T016a
  assumed. Measured over 86 confirmations, Jan-Jun 2026:
    250 fills total — 147 OPTIONS (59%), 103 equity
    91 of the 147 option fills expire the SAME DAY they were traded (62%) — 0DTE
    option notional $93,676 vs equity notional $771,905
  THE DEFECT: `data/schwab.py::_equity_leg` accepts only a transferItem carrying
  BOTH a symbol and a price, and everything else is reported as "TRADE with no
  priced equity leg (option, multi-leg, or corporate action)". Options are
  therefore classified as unmapped BY DESIGN. That was a defensible default when
  we believed this was an equity account; on the actual account it means the
  import silently discards 59% of his fills and essentially all of his 0DTE
  activity — which, on this evidence, IS his trading style.
  NOT A REGRESSION, AND NOT GEMINI'S MISS: T016a was reviewed and signed PASS
  against the assumption stated in its own docstring. The assumption was wrong,
  and the data arrived afterwards. That is what "reconciliation is the acceptance
  criterion" (D026) was for — it caught this before any behavioural conclusion
  was drawn from a 41%-complete import.
  KNOCK-ON, and the reason this is not just an import ticket: every behavioural
  module assumes shares. `analysis/attribution.py` FIFO has no contract
  multiplier, T091b holding periods are measured in DAYS when 62% of his option
  trades live for HOURS, and T069's sizing drift compares notionals that would be
  100x wrong if a contract were counted as a share.
  FIXED IN T105: `_equity_leg` became `_security_leg` — it accepts an OPTION
  transferItem, falls back to `underlyingSymbol` when the OCC symbol is absent,
  and explicitly skips CURRENCY and FEE legs (both of which can carry a price and
  would otherwise be mistaken for the fill). Option fills are marked
  `fill_type="option"`, which is what lets attribution apply the multiplier.
  Analysis side: `contract_multiplier()` returns 100 for an option fill, and the
  single "intraday" bucket became minutes / hours / same_day. That split is the
  point — with 62% of his option trades expiring the same day, a 20-minute scalp
  and a 7-hour hold were being reported as the same behaviour.
  T103 is unblocked once T105 is reviewed.
- I019 [RESOLVED 2026-08-17 — the app reached "Ready For Use"; the owner ran
  schwab_auth.py successfully (the script's built-in read-only probe verified
  the token before he walked away), wrote SCHWAB_REFRESH_TOKEN via --write and
  set SCHWAB_ACCOUNT_NUMBER. Standing operational fact, not a bug: the refresh
  token EXPIRES ROUGHLY WEEKLY — "token refresh failed" means rerun
  schwab_auth.py, not a defect. T016 live acceptance unparked; owner runs
  scripts/reconcile_schwab.py against a statement month next.]
  Original record follows for the paper trail:
  I019 [SCHWAB-SIDE, CONFIRMED — waiting on Schwab review] (2026-08-16)
  SYMPTOM: `python scripts/schwab_auth.py` opens the browser fine, the owner logs
  in and accepts the terms, and Schwab then LOGS HIM OUT with "We are unable to
  complete your request. Please contact customer support for further assistance."
  — while an email arrives saying his access preferences were updated.
  READING OF IT: the two halves disagree, and that is the tell. The ACCOUNT side
  of the link succeeded (hence the email); the APP side could not complete (hence
  the error and the logout). Nothing in this repo participates in that step, so
  no code change here can fix it.
  CONFIRMED BY THE OWNER 2026-08-16: the app status reads **"Modification
  Pending"**. He changed the callback URL after approval, which reset it. Note
  the exact string — the docs describe `Approved - Pending` (first approval) but
  an EDIT produces `Modification Pending`, and that is what to search for.
  Resolution is to WAIT; every further edit restarts the review.
  ORIGINAL DIAGNOSIS, per schwab-py's troubleshooting: the app is in a pending
  status rather than `Ready For Use`. The name is genuinely
  misleading — it contains the word "Approved" while NOT being usable — and
  Schwab resets an app to Pending on ANY edit, including changing the callback
  URL. If the owner edited the callback after approval, that alone would explain
  this. Approval is manual and takes a few days; nobody can speed it up.
  SECOND CANDIDATE: callback mismatch. Schwab compares byte for byte — scheme,
  case, port, trailing slash. Our .env holds `https://127.0.0.1` (17 chars,
  verified via env_check). The app must hold exactly that string.
  RULED OUT: the authorize URL format. Ours is
  `/v1/oauth/authorize?client_id={key}&redirect_uri={callback}`, which matches
  the documented form; both parameters are URL-encoded and a test asserts it.
  DONE HERE: schwab_auth.py now prints both causes BEFORE opening the browser,
  and names this exact symptom pair (error + preferences email) so it is
  recognised rather than debugged from scratch.
  OWNER ACTION: check the app's status field at developer.schwab.com. If it says
  Approved - Pending, wait. If it says Ready For Use, compare the callback string
  character by character against .env.
- I018 [FIXED 2026-08-16 — CI was red for ~80 tickets]
  CORRECTIONS FIRST, both mine: Claude repeatedly said "CI is dark" and that
  T005's push was outstanding. Wrong — the owner had been pushing all along
  (reflog: origin/main == local main, 7 Actions runs) and told Claude so. Claude
  also claimed CI would have caught the T069 `captured_at` bug; it would not, as
  CI runs the same green pytest suite. Only the type checker could.
  ROOT CAUSE: `test_market_latest_combines_trade_and_quote` overrode ONE of the
  endpoint's two dependencies. T036b gave /api/market/{symbol}/latest a second
  one — `get_alpaca_client`, for the session-aware freshness verdict — and the
  test left the real one in place. The real one needs credentials, so:
    machine with a .env  -> 200, green, for ~80 tickets
    fresh checkout / CI  -> 503, red
  Nobody saw it because the previous pushes were 2026-08-11; today's pushes
  surfaced it.
  HOW IT WAS FOUND, since guessing failed twice: reproduce, do not theorise.
  A clean venv (only backend/requirements.txt) PASSED — so not a dependency.
  The owner ran Python 3.11 locally and PASSED — so not the version. What was
  left was a FRESH CHECKOUT: `git ls-files -z | tar --null -T - -cf - | tar -x
  -C /tmp/cico`, which has no .env, no models/, no untracked files. That failed
  on the first run, naming the test.
  FIX: the test now overrides `get_alpaca_client` with a credential-free
  MockTransport stand-in. Fresh checkout: 693 passed, 4 skipped, lint clean.
  RULE ADDED: a test claiming "no network" must override EVERY dependency of the
  endpoint it calls, not just the one it is interested in.
  GUARD ADDED: scripts/verify.py now prints an environment banner before running
  — python version, whether .env is present, which optional modules are
  installed, whether the kokoro model is there — and adds a note after a PASS
  when a .env was in play. I016 and I018 are the same bug shape (green where the
  thing exists, red where it does not) and hit twice in one day; the banner makes
  two agents' conflicting PASS/FAIL reports immediately comparable.
  REPRO for the next time this shape appears:
    rm -rf /tmp/cico && mkdir -p /tmp/cico
    git ls-files -z | tar --null -T - -cf - | tar -x -C /tmp/cico
    cd /tmp/cico && python scripts/verify.py
- I017 [FIXED 2026-08-16 in T100] `LLM_TIMEOUT_SECONDS` reached both httpx providers
  and NOTHING in llm_claude_sdk.py — the owner's configured brain (I015). So the
  remediation offered for I014 ("if timeouts repeat, add LLM_TIMEOUT_SECONDS=600")
  was inert on his setup: a knob he could turn that did nothing, which is worse
  than no knob, because it looks like the fix was tried.
  FIX: the provider now carries `self.timeout = settings.llm_timeout_seconds` and
  wraps the SDK stream in `asyncio.wait_for`. Chose wait_for over an SDK option
  because the installed claude-agent-sdk exposes no per-query timeout and this
  works regardless of version; on expiry the generator is CANCELLED, so a
  half-streamed reply is never returned as though it were complete.
  The message is worded identically to the httpx providers on purpose — the owner
  should not have to work out which brain answered to know what to change.
  Tested: a query that never finishes raises LLMError rather than hanging, which
  matters because a hang means the I014 recovery path never runs and the turn is
  lost instead of resumable. A test also asserts the wording matches across both
  modules, so a future edit cannot let them drift apart.
  HOW IT WAS FOUND, worth keeping: a pyrefly sweep flagged
  `build_provider(s).timeout` as "ClaudeSDKProvider has no attribute timeout".
  That flag was a FALSE POSITIVE for the test — build_provider returns
  OpenAIProvider there — but the union member it named turned out to be a real
  hole in the provider it named. Worth remembering when triaging checker noise.
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

