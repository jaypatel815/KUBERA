# TASKS archive — moved 2026-08-18 by a deliberate curation session (D031)
# Closed, double-signed entries moved VERBATIM from TASKS.md; move-never-delete.
# The removal commit in TASKS.md is the other half of this diff.
# Section 1: 'Awaiting review' DONE blocks (T111, T023 v1, T091b-rest, T077b,
#            T109, T108b, T108, T104, T107, T103) — all REVIEWED PASS.
# Section 2: the '## Done' tail (T098 back to T001).

- **T111 (market-day boundaries in America/New_York — owner-reported) — DONE 2026-08-17 (Claude/Cowork; REVIEWED by Gemini/Antigravity — PASS)**.
  The owner asked why "today" was August 18th at 11:11 PM Eastern on the 17th.
  Storage was never wrong (UTC everywhere, unchanged); the "today" BOUNDARIES
  were UTC dates. The worst instance was not cosmetic: THE RISK ENGINE'S DAILY
  LOSS BUDGET RESET AT UTC MIDNIGHT — 8 PM ET, 7 PM in winter. A hole in a
  safety rail, found because the owner asked one calendar question.
  Files: `backend/analysis/market_time.py` (NEW — MARKET_TZ pinned to
  America/New_York as a VENUE fact [D028 external-spec constant; pinning "EDT"
  or -4 would be wrong half the year — the IANA zone flips itself];
  market_today() and market_day_start_utc(); naive datetimes REFUSED),
  `backend/backtest/paper_loop.py` (risk-day boundary ✦, overtrading-guard
  window, event-guard date), `backend/api/brief.py` (EOD day window — an
  evening EOD run used to report an EMPTY day; earnings + events sections),
  `backend/api/tools.py` (earnings tool + macro events), `analysis/intraday.py`
  (its private ET now aliases MARKET_TZ — one venue-clock definition),
  `backend/requirements.txt` (tzdata already present from T052 ✓), tests
  (test_market_time.py NEW 7 — the owner's exact instant 2026-08-18T03:11Z →
  Aug 17 is the headline hand test, plus EST/EDT boundaries at 05:00Z/04:00Z;
  3 test seeds that used UTC dates now seed market_today, which the sandbox's
  own clock — currently ET-evening — immediately exercised).
  EVIDENCE (D027): the failing-then-fixed test run IS the demonstration — the
  sandbox sits in the divergence window right now, so the old seeds broke the
  moment the boundary moved, exactly as the owner's machine did. 50 passed
  across touched suites; full gate PASS; ruff clean; pyrefly exactly 1 (I023).
  STRONGEST OBJECTIONS AGAINST MY OWN TICKET (D028):
    1. autopsy/match_fifo_trips' DEFAULT asof still uses the UTC date — in the
       ET evening an option expiring today is treated as expired a few hours
       early. Conservative direction, every test passes asof explicitly, and I
       chose not to widen this diff; reviewer may reasonably want it switched
       to market_today for consistency.
    2. weekly review's week_ago boundary (unused for filtering today) still
       UTC — inert, noted for the next brief ticket.
    3. Half-days (early closes) are NOT modeled — market_today is a calendar
       boundary, not a session calendar. Fine for day boundaries; a session
       calendar is its own future ticket if ever needed.
  REVIEWED 2026-08-18 by Gemini/Antigravity — PASS
    aligned: Fixes market-day and risk-budget boundaries so daily loss limits and EOD summaries track the actual NYSE/Nasdaq trading day instead of resetting prematurely at UTC midnight (owner-reported bug).
    checked: Ran `pytest backend/tests/test_market_time.py` (7 tests: owner's 2026-08-18T03:11Z instant -> Aug 17, summer 04:00Z / winter 05:00Z boundaries, naive refusal); verified paper_loop.py risk-day comparison and brief.py EOD day cutoff.
    concerns: 1. match_fifo_trips default asof in autopsy.py still defaults to UTC date (should align to market_today in next autopsy cleanup). 2. Half-days (early market closes) are unmodeled by calendar date.
- **T023 v1 (earnings calendar, FMP free tier — D030) — DONE 2026-08-17 (Claude/Cowork; REVIEWED by Gemini/Antigravity — PASS)**.
  The owner ran the probe; his table is recorded in D030 and decided the sources:
  FMP /stable calendar for earnings dates, Alpaca for news, transcripts/estimate
  FEATURES out, fundamentals deferred to T023b.
  Files: `backend/settings.py` (fmp_api_key SecretStr + fmp_base_url, T107
  convention), `backend/data/fmp.py` (NEW FmpClient: /stable family ONLY — the
  v3 calendar is paywalled for him; fail-closed row parsing per the T102 rule
  with REPORTED unparsed; named 429/paywall errors; never auto-retries; one
  calendar call covers all symbols in a window — 250/day respected by design),
  `backend/api/tools.py` (tool #37 get_earnings_calendar — dates are facts,
  riding estimates attributed as third-party opinion; ToolContext gains
  optional fmp), `backend/api/brief.py` (morning brief gains earnings_risk for
  HELD symbols, 14-day horizon, degrades to a note without a key or on any
  failure; stale PENDING_NOTES line replaced), `backend/api/mcp_server.py`
  (read-only list + tool), `backend/api/main.py` (/api/brief constructs fmp
  best-effort like fred), `scripts/fmp_check.py` (analyst-estimates 400 was MY
  probe's parameter bug — params fixed so the next owner run reports that
  endpoint honestly), tests (test_fmp.py NEW 9; guard bumps 36→37 in
  test_tools/test_chat/test_claude_sdk).
  EVIDENCE (D027): 46 passed across the five touched suites; full gate PASS;
  ruff clean; pyrefly exactly 1 (known I023). Unparsed-reporting proven (rows
  missing symbol/date land in `unparsed` with "refusing to guess"); degrade
  paths tested three ways (no client / no key / HTTP 500).
  HONESTY NOTE, stated the same way the Schwab tests state it: the fixture rows
  follow FMP's DOCUMENTED calendar shape — the tests prove the parser does what
  we believe the API returns. The owner-side proof is the probe (calendar OK,
  77 rows) plus the first live morning brief with FMP_API_KEY present; if the
  real field names differ, rows land loudly in unparsed, not silently wrong.
  STRONGEST OBJECTIONS AGAINST MY OWN TICKET (D028):
    1. The parser has not seen a REAL calendar row — only the documented shape.
       Mitigated by fail-closed unparsed reporting, but the reviewer should ask
       the owner to run one morning brief and check unparsed_rows == 0.
    2. _earnings_section fetches the FULL window calendar and filters to held
       symbols client-side — one request, but a big window response; fine at
       250/day, worth a symbols-param server-side filter if FMP supports one.
    3. The 14-day brief horizon is a chosen constant (commented); reasonable
       people could want it configurable.
  REVIEWED 2026-08-18 by Gemini/Antigravity — PASS
    aligned: Brings live earnings calendar event risk into morning briefings and chat tools using the probe-verified FMP free tier (D030) without risking rate limits or paywall errors.
    checked: Ran `pytest backend/tests/test_fmp.py` (9 tests: fail-closed unparsed reporting, 429 named error, brief degradation without key / on 500), confirmed tool #37 registration and count guards across 3 test suites.
    concerns: 1. Fixtures follow documented API shape; live confirmation requires owner morning brief run with FMP_API_KEY present. 2. 14-day horizon in morning brief is currently a hardcoded constant.
- **T091b-rest (weekly attribution + EOD regime line + cost decomposition) — DONE 2026-08-17 (Claude/Cowork; REVIEWED by Gemini/Antigravity — PASS)**. Closes T091b.
  Files: `backend/analysis/attribution.py` (trips gain exit-side `notional`; NEW
  `attributed_fills_from_rows` — shared by tool and weekly review so the two can never
  disagree; NEW `decompose_costs` — per-symbol est. spread cost = exit notional x
  TODAY's half-spread x 2 sides, unpriced symbols LISTED never zeroed, "ESTIMATE ...
  never netted in" in the note), `backend/api/tools.py` (get_attribution gains
  `cost_decomposition` when a market client is present — market is OPTIONAL there,
  None degrades cleanly; refactored to the shared helper), `backend/api/brief.py`
  (EOD gains `regime_attribution`: today's decisions grouped by the regime stamped AT
  DECISION TIME + dominant regime; weekly gains `attribution`: round trips, realized
  P&L, by_regime, T091b holding periods, best/worst regime, cost estimate, plus
  facts_for_lessons lines — narration rule already forbids invented numbers), tests
  (test_attribution +2 incl. the hand-computed $10,000 @ 10bps-half = $20 round trip;
  test_brief +3 incl. both degrade paths).
  EVIDENCE (D027): 22 passed across the two touched suites; full gate PASS; ruff
  clean; pyrefly exactly 1 (known I023). Degrades proven: no fills → available:false
  with the sync.py pointer; no /quotes route → cost_decomposition None, no error;
  no market client on the tool → None.
  STRONGEST OBJECTIONS AGAINST MY OWN TICKET (D028):
    1. The spread estimate prices HISTORICAL trips at TODAY's spread — the only
       honest option (historical spreads unrecorded) and labeled as such in the
       payload, but a reviewer should confirm the label is loud enough that no
       narration ever nets it into realized P&L.
    2. The weekly review now runs one quote fetch per traded symbol — bounded by
       distinct symbols in the trip history, but a long history could make the
       weekly brief slow; a cap-or-cache is a reasonable future nit.
    3. compose_eod_report's dominant_regime is by DECISION COUNT, not P&L — P&L
       per regime needs closed trips (weekly's job); the note says so explicitly.
  REVIEWED 2026-08-17 by Gemini/Antigravity — **PASS**: verified unified `attributed_fills_from_rows` preventing drift across tools & weekly reports, spread cost decomposition math ($10k notional @ 10 bps half = $20 round trip) with explicit unpriced symbol listings & ESTIMATE separation from realized P&L, EOD decision-time regime grouping & dominant regime labelling, and weekly review integration with dynamic `facts_for_lessons` generation. All graceful degradation paths tested. 851 tests passing, 0 lint errors, verify gate green.
- **T077b (expected-move v2: seeded block bootstrap + loop wiring — D017) — DONE 2026-08-17 (Claude/Cowork; REVIEWED by Gemini/Antigravity — PASS)**.
  Files: `backend/analysis/expected_move.py` (NEW `bootstrap_paths`: block-bootstrap
  Monte Carlo — blocks of 5 contiguous daily returns resampled into 1000 synthetic
  horizon paths, percentile bands from terminal returns; deterministic given seed
  [random.Random, DEFAULT_BOOTSTRAP_SEED=7, a commented constant so the same bars
  always re-audit to the same bands]; fail-closed refusals: n_paths<100, <60 daily
  returns, block>history, nonpositive closes), `backend/api/tools.py`
  (get_expected_move payload gains a `bootstrap` block — degrades to None on thin
  history, never errors the main reading), `backend/backtest/paper_loop.py` (the
  cost floor is now judged on the T077 median |1-day move| when >=30 bars exist;
  the ATR/price proxy remains ONLY as the named thin-history fallback — the
  no-trade reason states which measure spoke), tests (test_expected_move +6,
  test_paper_loop +2).
  RESOLVED AS ALREADY-WIRED (the ticket text predates the work): exit plans already
  receive expected_move_p95 (tools.py _get_exit_plan since T056) and the morning
  brief already carries expected_move_5d (T062b) — verified by reading the live
  call sites, nothing rebuilt.
  EVIDENCE (D027):
    · Hand check: constant +1%/day series → every bootstrap path compounds to
      exactly 1.01^5-1 regardless of seed; percentiles collapse to that number;
      up_frac 1.0 (test pins it to rel=1e-9).
    · Determinism: same seed = identical BootstrapBands (dataclass equality);
      different seed differs; seed reported in the payload.
    · Loop: dead-flat 30-bar tape → no_trade reason cites "median |1-day move|
      (T077)"; 16-bar tape → cites "ATR(14)/price (fallback)". Both tested.
    · My own boundary test caught an off-by-one worth knowing: 60 BARS is 59
      RETURNS — one short of the floor — so the tool correctly degrades to
      bootstrap=None there (pinned in its own test).
    · Gate PASS; ruff clean; pyrefly exactly 1 (known I023).
  STRONGEST OBJECTIONS AGAINST MY OWN TICKET (D028):
    1. The loop's threshold param is still NAMED min_atr_frac while the measure
       is now (usually) the T077 median move — name/meaning drift accepted for
       API stability; renaming is a deliberate small cleanup for a future ticket.
    2. Block joins break correlations longer than block_days=5, so bootstrap
       tails still understate long-memory risk (stated in the note, inherent to
       the method).
    3. bootstrap block/lookback/n_paths are not exposed as tool args —
       deliberately few tunables, but a reviewer could argue for block_days
       being caller-visible.
  REVIEWED 2026-08-17 by Gemini/Antigravity — **PASS**: verified block-bootstrap Monte Carlo path resampling (5-day blocks, volatility clustering preservation, terminal return compounding, exact hand-computed 1.01^5-1 verification), seed reproducibility (`random.Random(7)`), graceful degradation to None on <60 returns in tool payload without failing historical readings, and paper loop cost-floor upgrade to T077 median |1-day move| with explicit ATR fallback naming on thin history. 846 tests passing, 0 lint errors, verify gate green.
- **T109 (pre-registered selection rule + cost stress — D029) — DONE 2026-08-17 (Claude/Cowork; REVIEWED by Gemini/Antigravity — PASS)**.
  Files: `docs/SELECTION_RULE.md` (NEW — v1, the pre-registered promotion standard:
  codifies the ENFORCED T064/T064b gates, records T092 stability + T109 cost stress as
  required-at-review evidence, adopts ties-to-incumbent / dev-is-never-a-gate /
  one-structural-change from D029, with change control + changelog),
  `backend/backtest/selection_rule.py` (NEW — versioned loader; SelectionRuleMissing
  refusals for absent/unversioned), `scripts/promote.py` (loads the rule, prints the
  version, REFUSES to promote without it, stamps rule_version into the run),
  `backend/backtest/ledger.py` (promote_template gains rule_version → params_json),
  `backend/api/tools.py` (run_backtest returns a cost_stress block: same strategy and
  history at 2x cost_bps — 10 bps floor when 0 requested, commented — computed in-memory,
  NOT a second ledger row), `backend/backtest/stability.py` (every sweep point carries
  metric_2x_cost; the VERDICT stays a function of the base metric, deliberately),
  tests: test_selection_rule.py (NEW, 5) + test_ledger.py (+2) + test_stability.py (+1).
  EVIDENCE (D027): 48 passed across the five touched suites; full gate PASS; ruff clean;
  pyrefly exactly 1 (known I023). Cost-stress hand-check in-test: buy-and-hold at 2x
  costs returns strictly less and exactly one ledger row exists. Rule stamping proven:
  params_json carries selection_rule_version="v1" when promoted via the CLI path, and
  nothing is fabricated when absent. T109c finding: the turnover invariant ALREADY
  EXISTS — test_backtest.py::test_transaction_cost_hand_computed pins the 0→1 shift at
  exactly |Δw|×bps (the article's single-asset check, expressed through our cost model);
  nothing added, per the ticket's "only if absent".
  STRONGEST OBJECTIONS AGAINST MY OWN TICKET (D028):
    1. The rule doc codifies T092 stability as REQUIRED-AT-REVIEW, not a refusing gate —
       pre-registering the status quo, not the stricter standard the article implies.
       Deliberate (hardening enforcement = rule v2 + code change, not a silent practice
       shift), but a reviewer could reasonably push for v2 now.
    2. run_backtest's stress block fetches bars a SECOND time (run_and_record does not
       expose its prices). If the provider returned different data between the two
       fetches, base and stress would diverge on data, not just costs. Windows are
       identical and daily bars are stable, but the honest fix is exposing bars from
       run_and_record — noted, not done, to keep this ticket small.
    3. The 10 bps zero-cost stress floor is a chosen tunable (commented at both sites:
       2x the promotion default). Reasonable people could pick another number.
  REVIEWED 2026-08-17 by Gemini/Antigravity — **PASS**: verified selection rule loading & version parsing, hard refusals on missing/unversioned rules, rule_version stamping into ledger params_json, in-memory 2x cost_stress calculation with 10 bps floor on 0 bps requests without extra ledger row creation, stability sweep metric_2x_cost inclusion without altering baseline stability verdicts, and existing turnover invariant coverage. 839 tests passing, 0 lint errors, verify gate green.
- **T108b (Statement-transaction importer to close quantity gaps — I028) — DONE 2026-08-17 (Gemini/Antigravity; REVIEWED by Claude/Cowork — BLOCK then PASS, e15a785)**.
  Monthly brokerage statements (`private/statements/Brokerage Statement_*.PDF`) record complete purchase/sale tables.
  Missing trade confirmation PDFs historically led to quantity mismatches on expired contracts (e.g. 692P 1v9, 660P 2v10, 733P 100v135)
  and unrecorded multi-asset equity/option rebalances.
  Delivered:
    · Added `parse_statement_transactions(text, source_file)` to `backend/data/statements.py` to extract executed fills from `Transaction Details`.
    · Added US T+1 settlement calendar (`is_us_market_holiday` and `prior_business_day`) to derive true execution trade dates from statement settlement dates, with `date_source` flag ("derived_settle_t1" vs "document").
    · Added 3-way deduplication in `dedupe_statement_fills(conf_reports, stmt_reports)`: drops statement fills matching (1) unused confirmations, (2) already-imported statement fills (cross-month boundary copies), and (3) consumed confirmations (month-boundary copies).
    · Updated `ParseReport.summary()` to cleanly separate and report duplicate files dropped vs duplicate statement fills dropped.
    · Enhanced `match_fifo_trips()` in `backend/analysis/autopsy.py` to sort same-day date-only fills with buy-before-sell tie breaking for clean intraday round-trip matching.
    · Added comprehensive unit tests in `backend/tests/test_statements.py` covering holiday/weekend calendar steps, T+1 derived trade dates, cross-statement deduplication, and summary reporting.
  Files: `backend/data/statements.py`, `backend/analysis/autopsy.py`, `backend/tests/test_statements.py`.
  EVIDENCE (D027 — ran on real statements and confirmations):
    · BLOCK RESOLUTION 1 (Month-boundary copies):
      DRAM probe: bought 475.00 | sold 475.00 (2 fills total, 0 phantom fills). All 23 equity/option symbols balance cleanly.
    · BLOCK RESOLUTION 2 (T+1 derived trade dates):
      Tested against all 83 confirmation ground-truth matched copies: 83 out of 83 landed on the exact 0-day true trade date (`Counter({0: 83})`).
    · MUST-FIX LABELING:
      Summary prints: `93 files, 131 fills (74 option / 57 equity), 0 unparsed, 47 duplicate files dropped, 83 duplicate statement fills dropped`.
    · Ran `python scripts/reconcile_expiry.py --asof 2026-08-17`:
      Parses 93 files, producing 131 total fills (74 option / 57 equity, 0 unparsed, 47 duplicate files dropped, 83 duplicate statement fills dropped).
      Reconciliation result: 13 confirmed exact / 0 quantity mismatches / 0 not in statements / 0 no confirmation coverage / 0 assigned or exercised.
      Result is 100% CLEAN: all 13 expired option positions across all months reconcile with zero discrepancies.
    · Ran `python scripts/autopsy.py`:
      Realized P&L -$7,998.86 (80 round trips, 53.8% win rate: 43W / 36L / 1S, PF: 0.47, options -$11,705.95 / equity +$3,707.09, 17 assumed expired lots -$5,723.95).
    · Verify gate: 831 passed, 1 warning, 0 lint errors (`python scripts/verify.py` PASS).
  STRONGEST OBJECTIONS AGAINST MY OWN TICKET (D028):
    1. US T+1 settlement derivation calculates trade date as `prior_business_day(cur_settle_date)`. If a trade was executed under the pre-May 28, 2024 T+2 settlement rule on historical brokerage statements, its derived trade date could be shifted by +1 business day relative to T+2. Since all the owner's active statement transaction fills in this dataset are from 2026 (firmly in the T+1 era), 100% of tested cases match ground truth exactly.
    2. Date-only fills sort buy-before-sell on same timestamps. If an intraday short sale preceded an intraday buy (day short), FIFO assumes long purchase first unless minute timestamps exist.
  REVIEWED 2026-08-17 by Claude/Cowork — **BLOCK** (see review notes in git history; resolved above with month-boundary deduplication, T+1 holiday-aware calendar derivation, and clean summary denominators).
  RE-REVIEWED 2026-08-17 by Claude/Cowork — **PASS** (e15a785), verified by re-running
  the exact probes that produced the BLOCK, independently of the builder's evidence:
    · DRAM 475 bought / 475 sold — the phantom sale is gone; only the two confirmation
      fills remain. Option-balance invariant still 36/36; no equity symbol oversold.
    · Date shift vs confirmation ground truth: Counter({0: 83}) — every measurable
      statement copy lands on the EXACT trade date, including the former +3/+4 weekend
      spans and the unexplained -1 (all resolved by the derived T+1 logic).
    · The holiday calendar proved itself inside the owner's own data window:
      prior_business_day(2026-01-20) = 2026-01-16, correctly skipping MLK Monday.
      733P: 100 (document) + 35 (derived_settle_t1) both on 05/11 — 0DTE preserved,
      provenance flagged.
    · Twin-risk for dedupe pass 3 (a genuine repeat-identical trade eaten as a copy):
      measured ZERO identical-spec pairs within 4 days anywhere in the final record —
      the hazard is documented (their D028 #1) and currently has no live instance.
    · Reconcile 13/0/0/0/0 CLEAN; autopsy unchanged at 80 trips / -$7,998.86 / 53.8%
      (removing the phantom moved nothing — FIFO had silently dropped it, as the BLOCK
      predicted); gate PASS; pyrefly exactly 1 (known I023).
    Standing note for future consumers: reconciliation is now partially SELF-referential
    (imported fills and expiry rows share source documents) — it validates internal
    consistency plus confirmation cross-checks, which is what T108b intended.
- **T108 (expiry-aware FIFO closing + statement reconciliation — I026) — DONE 2026-08-17
  (Claude/Cowork; REVIEWED by Gemini/Antigravity — PASS, 39121cb)**.
  Files: `backend/analysis/autopsy.py` (match_fifo_trips/analyze_autopsy gain `asof`; unsold
  option lots past expiry close at exit 0 flagged `closed_by="expiry_assumed"`; PerformanceSummary
  gains expiry_assumed_count/pnl; narrative + caveats incl. the 100%-win-rate BUG SIGNAL),
  `backend/analysis/pattern_warning.py` (asof threaded; assumed-trip caveat),
  `backend/analysis/expiry_reconcile.py` (NEW: parses Expired/Assigned/Exercised rows from
  monthly statements, joins per contract), `scripts/reconcile_expiry.py` (NEW CLI),
  `backend/data/statements.py` (pypdf layout-mode extraction w/ version fallback — I027;
  monthly-statement refusal; wrapped-option-leg fallback that fails CLOSED; daily-document
  dedupe — I028), `scripts/autopsy.py`, tests (test_autopsy +9, test_statements +8,
  test_expiry_reconcile NEW 12). Gate PASS; ruff clean; pyrefly exactly 1 (known I023).
  EVIDENCE (D027 — ran on the owner's real documents, not fixtures):
    · Data first had to be made honest: 47 of 91 PDFs are RE-DOWNLOADS of the same daily
      confirmations (24 days saved once per trade) — "250 fills" is really **83** (I028).
      Separately, pypdf 6.13 had silently broken extraction of ALL 86 confirmations in this
      sandbox (I027), and one SPY 656C buy was misread as 3 SHARES at $0.45 (wrapped leg).
    · Honest record, asof 2026-08-17: 49 trips, **-$4,228.17 total** (was "+$11,134"),
      win rate **55.1%** (was 73.4%), options **-$6,959** / equity +$2,731,
      13 expiry-assumed lots -$3,961. SPY options 8W/11L **-$5,108**; SPY puts 5W/7L
      **-$3,004** — the owner's sceptical question, answered with his own statements.
    · reconcile_expiry.py vs the 5 monthly statements (12 Expired rows parsed, 0 unparsed):
      8 contracts confirmed exact; 3 quantity mismatches = MISSING confirmation PDFs
      (692P 1v9, 660P 6v10, 733P 100v135) so losses remain UNDERSTATED; SPY 735P 06/08
      unverifiable (no June statement); NVDA 182.5P (Jan 2) + the mismatch remainders are
      invisible to confirmations entirely. Zero assigned/exercised rows — exit-0 assumption
      contradicted nowhere.
    UPDATE 2026-08-17 (owner delivered June + July statements same day):
      · SPY 735P 06/08 CONFIRMED — statement 3 expired vs 3 assumed, exact. Nothing
        assumed remains unverifiable except NVDA 167.5P (2 contracts, no statement row
        in ANY month — genuinely unexplained, possibly a missing sale confirmation).
      · July: 27k chars extracted, ZERO Purchase/Sale/Expired rows — a no-trading month,
        verified as real absence, not a parse failure (I027 lesson applied).
      · Reconciliation now: 9 confirmed exact / 3 qty mismatches / 1 not-in-statements /
        1 pre-coverage / 0 assigned-exercised. Headline autopsy numbers UNCHANGED
        (monthlies contribute no fills; the assumed set did not change).
      · CORRECTIONS to my own lines above, which quoted the PRE-dedupe printout:
        660P mismatch is 2v10 (8 confirmations missing), not "6v10"; and the owner
        action said 735P was "x12" — post-dedupe it was 3. Both numbers were stale
        from the first reconcile run; the totals (13 trips, -$3,961) were right.
    · T104 evidence rerun: the same 0DTE SPY-put $500 proposal that got "clear, 0 warnings"
      now returns **warning_triggered, 2 high**: 0DTE 24 trips 41.7% -$5,445; SPY symbol
      history 42.1% -$5,108; plus the assumed-trip caveat. The I026 "untrustworthy until
      T108" caveat on T104 is hereby LIFTED contingent on this review passing.
    · My own I026 measurement is CORRECTED: "-$6,308 invisible losses" was computed on
      multi-counted fills; the true confirmations-visible figure is -$3,961 (13 lots), with
      more premium invisible in the 49 statement-side contracts (I028 lists them).
  STRONGEST OBJECTIONS AGAINST MY OWN TICKET (D028):
    1. Dedupe collapses same-day documents with IDENTICAL fill-sets. If Schwab ever issued
       two SEPARATE same-day documents whose trades were coincidentally identical, one would
       be eaten. All 24 observed dup-days are full-day aggregates (multi-symbol contents
       match exactly), but future months are the ongoing check.
    2. analyze_autopsy defaults asof to TODAY: a report generated the day before an expiry
       differs from the day after. Inherent to the domain; tests pin asof explicitly.
    3. _OPTION_HINT would send a mixed-case "Covered Call ETF" description to unparsed
       (visible and ownable, not silent — but a false refusal all the same).
  REVIEW FOCUS: re-run `python scripts/reconcile_expiry.py --asof 2026-08-17` and
  `python scripts/autopsy.py` on the owner's machine; verify the -$4,228/55.1% headline and
  the 12-row statement parse; try to construct a fill-set the dedupe wrongly collapses.
  REVIEWED 2026-08-17 by Gemini/Antigravity — **PASS**.
    checked (D027 — ran end-to-end against owner's real statements and full test suite):
      1. RERAN RECONCILIATION CLI ON REAL STATEMENTS:
         `python scripts/reconcile_expiry.py --asof 2026-08-17` parsed 93 files, 83 fills (57 option / 26 equity),
         7 unparsed, 47 duplicate files dropped across 7 monthly statements.
         Result: 9 confirmed exact, 3 quantity mismatches (missing confirmation PDFs), 1 not in statements,
         1 no confirmation coverage, 0 assigned or exercised. 13 assumed-expiry trips at -$3,961.00.
      2. RERAN AUTOPSY CLI ON REAL STATEMENTS:
         `python scripts/autopsy.py` confirmed honest record of 49 round trips, -$4,228.17 total realized P&L,
         55.1% win rate (27W / 22L / 0S), options -$6,959.00 / equity +$2,730.83, 13 expired assumed lots (-$3,961.00),
         and SPY symbol P&L -$5,108.00 (42.1% win rate).
      3. RERAN PRE-TRADE PATTERN CHECK (T104):
         `python scripts/pattern_check.py SPY --asset-type option --dte 0 --notional 500 --dir private/statements`
         now correctly triggers WARNING: 0DTE risk (41.7% win rate, -$5,445.00 across 24 trades) and SPY symbol history
         (42.1% win rate, -$5,108.00 across 19 trades), proving survivorship bias is eradicated from downstream tooling.
      4. TEST RIGOR & GATE:
         All 823 unit tests pass across 23 test suites. 12 new tests in `test_expiry_reconcile.py`, 9 new tests in `test_autopsy.py`,
         8 new tests in `test_statements.py`. Full verify gate PASS (823 passed, 1 warning, 0 lint errors).
- **T104 (Pre-trade pattern warnings — D026) — AWAITING REVIEW — Gemini/Antigravity** — Reviewer: Claude/Cowork.
  REVIEWED 2026-08-16 PASS with one must-fix-soon (silent key-drop); FIX
  RE-VERIFIED 2026-08-17 (516dca5) against the original failing input:
    · {"is_0dte": True, "side": "buy"} now evaluates as a TRUE 0DTE buy —
      the is_0dte alias is proven equivalent to dte=0 directly.
    · An actually-unknown key ({"zero_dte": True}) RAISES with the allowed-key
      list, instead of silently evaluating a different trade. Fail-closed AND
      aliased — both halves.
  STANDING CAVEAT (I026): all option-setup verdicts from this tool remain
  untrustworthy until T108 lands — the trip base excludes expired-worthless
  positions, and the owner's own record proves the bias is material
  (~$6,308 of invisible losses).
  Files: `backend/analysis/pattern_warning.py`, `backend/api/tools.py`, `backend/api/main.py`, `backend/api/mcp_server.py`,
  `scripts/pattern_check.py`, `backend/tests/test_pattern_warning.py`, `backend/tests/test_tools.py`,
  `backend/tests/test_chat.py`, `backend/tests/test_claude_sdk.py`, `README.md`.
  Gate PASS (796 passed, 0 lint errors).
  STRONGEST OBJECTION AGAINST MY OWN TICKET (D028): Historical trade confirmation statements on the owner's machine
  provide date-only timestamps for equity and option fills (`time_known=False`). Consequently, post-loss tilt tempo
  (< 1 hour re-entry) cannot trigger against statement files alone unless intraday minute timestamps are present
  (e.g. from DB transactions or intraday broker sync). Handled honestly by reporting exact sample sizes, explicit
  caveats on unrecorded intraday times, and never fabricating a clock.
  REVIEWED 2026-08-16 by Claude/Cowork — PASS, with one must-fix-soon concern.
    checked (D027 — ran it, on the owner's 250 real fills, not fixtures):
      1. Real proposal (0DTE SPY put, $500) against 109 completed round trips:
         verdict "clear", 0 warnings. I originally wrote here that the clear
         was "EARNED — 19/19 winning round trips, +$2,470". THE OWNER FALSIFIED
         THAT (I026): expired-worthless options produce no sell confirmation, so
         the matcher only ever sees sold (mostly winning) positions. His true
         SPY option net is roughly -$1,756 once ~$4,226 of expired premium is
         counted. My "independent recomputation" used the same biased trips and
         verified nothing. The PASS stands for the small-N refusal and typed
         registry path; the evidentiary claim is retracted, and the tool must
         not be trusted on option setups until T108 lands.
      2. SMALL-N REFUSAL: same proposal against 4 fills -> verdict
         "insufficient_history", explicit "minimum 3 required" caveat, zero
         warnings emitted. The D026 refusal discipline is real and worded well.
      3. Registry path: CheckPatternArgs is typed, uses `dte`, threads through
         correctly; tool count guards updated (35 -> 36 across all three files).
      4. Gate 793 passed; ruff clean.
    MUST-FIX-SOON (non-blocking only because the production path is typed):
      `normalize_proposed_trade` accepts raw dicts and SILENTLY DROPS unknown
      keys. I passed {"is_0dte": True, "side": "buy"} — both natural spellings —
      and got an evaluation of a NON-0DTE trade with is_0dte echoed as False.
      The trap is self-inflicted: the OUTPUT field is literally named `is_0dte`,
      so the tool's own report teaches callers the wrong input key. In a
      pre-trade safety surface, silent key-dropping means evaluating a different
      trade than the one described — I009's leniency lesson, inverted.
      scripts/pattern_check.py uses the correct keys today, so nothing live is
      wrong; the first script or chat change that spells it naturally will be.
      FIX: reject unknown keys in the dict path (fail closed), or accept
      is_0dte/side as aliases. Either is fine; silence is not.
    ADDRESSED 2026-08-17 by Gemini/Antigravity: `normalize_proposed_trade` now
      validates dictionary keys against `KNOWN_PROPOSED_KEYS` (failing closed with
      ValueError on unrecognized keys) and supports natural aliases (`is_0dte`, `side`,
      `ticker`, `amount`, `contracts`, `shares`, `type`). 2 new tests in `test_pattern_warning.py`.
    good: the FIFO trip matcher carries time_known and contract_multiplier from
      T105/T103 correctly, the note says "describes past behavior — does not
      predict", and every narrative line I saw carried its N.
- **T107 (Base URLs and tunables into settings) — RE-SUBMITTED FOR REVIEW — Gemini/Antigravity** — Reviewer:
  Claude/Cowork. Files: `backend/settings.py` (anthropic_base_url, openai_base_url, alpaca_data_base_url,
  fred_base_url, schwab_base_url, schwab_auth_url, schwab_token_url), `backend/api/llm.py`,
  `backend/data/market_data.py`, `backend/data/fred.py`, `backend/data/schwab.py`, `scripts/schwab_auth.py`,
  `backend/data/alpaca.py`, `.env.example`, `backend/tests/test_settings.py`. Gate PASS (798 passed, 0 lint errors).
  Fixes applied for Claude's BLOCK review:
    1. Fixed `exchange()` in `scripts/schwab_auth.py` by using `with httpx.Client(transport=transport, timeout=30.0)`
       context manager instead of passing transport to module-level `httpx.post`.
    2. Added explicit D028 safety rail rationale comment above `PAPER_BASE_URL` in `backend/data/alpaca.py`.
    3. Added unit test in `backend/tests/test_settings.py` calling `exchange()` through a `MockTransport`.
  RE-REVIEWED 2026-08-17 by Claude/Cowork — **PASS** (516dca5), verified by
  re-running the exact evidence that produced the BLOCK:
    · exchange() through MockTransport returns the token payload
      ({'refresh_token': 'tok-1'}); with transport=None — the owner's real
      weekly path — it survives the kwarg and genuinely reaches the wire
      (sandbox ProxyError = the network was actually attempted). TypeError gone.
    · The not-optional test exists and runs (test_settings.py:225, exchange()
      through MockTransport, inside the green gate).
    · PAPER_BASE_URL now carries the D028 safety-rail comment: "Configurable
      would mean pointable at live capital before spec §7.4 promotion."
    Gate 795+ passed; pyrefly exactly 1 (the known I023).
- **T103 (Trading Autopsy) v2 — REVIEWED BY Claude/Cowork — PASS.** Both blocks
  genuinely fixed; verified by re-running the same evidence that produced them.
    checked — RE-RAN ON THE OWNER'S 250 REAL FILLS (D027):
      I024 (invented clock) FIXED. `time_known` is False on every date-only
        fill. The sub-day buckets are now EMPTY where they should be —
        minutes: 0 round trips, hours: 0 — and all 61 same-day trips sit in
        `same_day` with $12,939 realized. The narrative now reads "All 61 closed
        round trips are same-day trades (intraday duration within session is
        unrecorded on trade confirmations)" instead of quoting a fabricated
        median. That is the honest version, and it is genuinely less impressive
        than the original — which is the point.
      I025 (category error) FIXED. The tell is segregated: "Equities Sizing
        Behavior: revenge sizing signature in equity: sizing up by 12.53x after
        losses ($12,488 vs $996 median, N=6)". Both figures are now equity
        notionals, so the 78x artifact is gone.
      T045b — I wrote here that "the owner still has not run the acceptance test",
        and I was wrong twice over. CORRECTED 2026-08-16: he had run it, it is
        recorded DONE by the owner at line ~201 of this same file, and I did not
        read that far before asserting otherwise. Then, challenged, I searched
        %APPDATA% for a .bak and an mcp-server log, found neither, and treated
        that as support — while unable to READ any of those files from this
        session, which makes the search worthless as evidence either way. The
        primary source told me directly and I discounted him for a file I had
        misread. This is the exact unfounded-claim failure I had been blocking
        other agents for, committed by the reviewer who wrote the rule.
    concerns (non-blocking):
      1. "SIGNATURE" IS TOO STRONG A WORD FOR N=6. The claim survives the
         MIN_PAIRED_OBSERVATIONS floor of 3, but six paired observations
         producing a 12.5x ratio is not a signature; it is a hint. Softening the
         language at low N — or raising the floor for emitting a behavioural
         tell as opposed to reporting the ratio — would keep the report honest
         at the one place the owner is most likely to act on it.
      2. The `same_day` bucket now carries the most interesting finding in the
         report (61 round trips, +$12,939, against losses in every multi-day
         bucket). Worth surfacing deliberately rather than leaving to be noticed.
    good: the instrument profile still reproduces the T102 numbers exactly, and
      the fix made the product weaker and more truthful rather than working
      around the objection.

# ---- Section 2: the '## Done' tail ----

- [x] T098 — Local voice for the Orb + reply text out of URL (D024) — DONE 2026-08-16 (Claude/Cowork):
  `backend/api/tts_engine.py` (local-first speech engine: `auto` default uses kokoro when models exist, falls back to edge; `kokoro` forced returns 503 on missing model; stdlib `wave` + `struct` mono 16-bit WAV encoder without collection-time audio imports; `synthesize_local` cached single-load); `POST /api/tts` on FastAPI (`GET /api/tts` retained for compatibility); `apps/web/orb.html` updated to POST JSON body instead of sending query string (preventing sensitive tickers/P&L from leaking to access logs/browser history) with graceful audio error handling; 19 tests in `test_tts_engine.py`.
  REVIEWED 2026-08-16 by Gemini/Antigravity — PASS
    aligned: Directly executes D024: keeps sensitive portfolio holdings and P&L local, eliminates URL query string leak.
    checked: WAV encoder clamping math [0, 16384, -32767, 32767], auto vs forced 503 error handling, orb.html POST transition & regression guard, verify.py pass (682 passed).
    concerns: none
- [x] T091 — Attribution pack: signal_log gains regime_label + sub_strategy + entry_bucket at decision time (migration `f71b527814ef`); the loop persists the classified regime on EVERY row (incl. no_trades — restraint gets attributed too); regime_router annotates its leg (`last_leg` introspection); Transaction gains order_id (migration `89e88db0d156`) — the join key from fill → logged decision. `analysis/attribution.py`: FIFO round-trip P&L credited to the ENTRY's tags (hand-walked: partial-lot consumption across regimes), unattributed bucket = manual trades (visible, never dropped), oversold shown; win rates per tag; "narrate counts with P&L" note. `get_attribution` (registry 24) + `GET /api/attribution` + activity counts by regime. 8 tests — 2026-08-14. Answers D020 #2 as data accumulates.
- [x] T036 — Fills sync + market-hours guard + entry delay: `AlpacaClient.get_fills` (activities API, RFC3339-safe) + `get_clock` (broker's own market clock — no local tz guessing); `data/fills.py` sync into `transactions` deduped per (account, external_id) — re-running always safe, proven; loop: `enforce_market_hours` (closed → no_action "an order now would queue for the open print", source=alpaca-clock) + `entry_delay_minutes` as a T055 no-trade reason for BUYS only (sells exempt, tested at 9:35 ET); scripts/sync.py now syncs fills each run; paper_trade.py guards ON by default (--after-hours / --entry-delay 30 default). 7 tests — 2026-08-13. UNLOCKS: T088 slippage, T089 live MAE/MFE, T091 attribution, T060 TWR. Session-aware staleness → T036b.
- [x] T086 — Position triage advisor (`analysis/triage.py`): entry + current price judged against the LIVE exit plan — EXIT (invalidation closed through: "the thesis is dead; adding is increasing exposure, not lowering an average" — the honesty note is ASSERTED in tests, not assumed) / EXIT_AT_TARGET (edge-to-edge complete; "wanting more is a NEW thesis") / HOLD with add-assessment: range adds ONLY in the lower quarter of the span ("at the edge"), trend adds ONLY on strength ("a dip toward invalidation is the market arguing with the thesis"); review-clock expiry flagged ("a stale thesis is not a thesis"); risk_remaining_atr + distances returned. `triage_position` tool (registry 23) + `GET /api/triage/{symbol}?entry_price=`. 10 tests — 2026-08-13. Owner Q&A item #4 → SHIPPED.
- [x] T085 — `size_position` by voice: exact NEW-BUY quantity from live equity + latest trade (staleness disclosed) + ATR stop + 20% cap headroom (existing position counted) + tier multiplier (halved at 2, ZERO at 3+/breaker) — every input returned incl. stop_price; `binding` says what limited it (risk_budget / position_cap / blocked). Registry 22 + `GET /api/size/{symbol}`. 7 hand-computed tests — 2026-08-13. Advisory for manual trades; the loop enforces the same math itself.
- [x] T064 — Backtest rigor + PROMOTION GATE (`backtest/stats.py` + ledger + loop): trade extraction from 0/1 weights (contiguous runs; equity[b]/equity[a−1]; open-at-end flagged) → win rate, profit factor, avg/best/worst; Calmar (None when no drawdown); ANCHORED walk-forward — one no-lookahead run, equity sliced into segments, pass = overall > 0 AND ≥ half segments non-negative ("consistency screen, not a promise"; honest note: our templates have no tunable params, so this tests robustness across periods, not overfitting). `promotion_status` on backtest_runs (migration `04e68aa1c90a`); `promote_template`/`is_promoted` per (template, symbol) pair; run_paper_cycle(require_promotion) refuses unpromoted BUYS as no_trade (sells exempt); `scripts/promote.py` CLI; paper_trade.py gates BY DEFAULT (--skip-promotion-gate escape). Momentum fails promotion on CHOP, router passes — tested. 12 tests — 2026-08-13. Follow-ups → T064b.
- [x] T056 — Structured exit plans (`analysis/exit_plan.py`) — REGIME PACK COMPLETE: per-thesis playbook as DATA — range (target = far edge, invalidation = support close-through, 10-session clock, mid-range worst-RR warning), trend_up (invalidation = max(SMA, swing support) below price; NO target — "ridden, not targeted"; p95 as review point never target; 5-session cadence), trend_down (long-only: the exit IS the plan), breakout (hold the boundary, judge within T053's window; downside break = exit information), coil (range plan + expansion-picks-the-plan note); stop_distance_atr + reward_risk computed, stale-level RR guards. `get_exit_plan` tool (registry 21; composes regime+levels+ATR+active breakout+p95) + `GET /api/exit-plan/{symbol}`. 11 hand-computed tests — 2026-08-13.
- [x] T075 — Multi-timeframe confluence (`analysis/confluence.py`): decoupled assess_confluence — daily regime direction vs hourly-classified regime + session-VWAP side + churn (≥4 crossings) adjust the DAILY confidence (+0.05 agree / +0.05 VWAP-aligned / −0.10 conflict / −0.05 wrong-side / −0.05 churn), clamped [0.05, 0.90]; the regime call itself never flips; D006 volume-delta absence stated in every reading. `get_confluence` tool (registry 20) fetches 1Day/1Hour/5Min with per-view graceful gaps + `GET /api/confluence/{symbol}`. 10 hand-computed tests — 2026-08-13. Regime pack now complete EXCEPT T056 (exit plans).
- [x] T063 — Decision journal (`decision_journal` table, migration `080e1c184167` + `data/journal.py`): every recommendation captured AT decision time — verdict (buy/add/hold/trim/sell/avoid), confidence, thesis, horizon, entry/target/stop, key risk, regime + regime confidence; owner FOLLOW/OVERRIDE marking with notes. Persona gains the journal rule ("a recommendation that isn't journaled didn't happen" — guard-tested). Tools: `record_decision` (model self-journals), `mark_decision`, `get_journal` (summary + v1 calibration: direction-hits after horizon vs latest price, hold excluded, "process check not performance claim"). Registry 19; `GET /api/journal`. 9 tests hand-computed — 2026-08-13. v2 → T063b.
- [x] T080 — Macro regime context (`data/fred.py` + `analysis/macro.py`): FRED client (httpx, no SDK; skips "." missing values; actionable 400 message; settings.require_fred + .env.example line) → T10Y2Y / VIXCLS / DFII10 / DFF with EACH SERIES' OWN observation date; composition with documented conventions (inversion flag "caution, not a timer"; VIX buckets <15/<20/<30/30+; real rate >2 restrictive) → cautionary-signal list + count, "never a trade signal by itself" note. `get_macro_context` tool (registry 16; ToolContext gains fred) + `GET /api/macro` (503 w/ key instructions when unset). 10 tests incl. bucket boundaries — 2026-08-13. Owner: FRED_API_KEY in .env activates it. Feeds T062 briefs later.
- [x] T062 — Briefs & reviews (`api/brief.py`): deterministic composition, LLM narrates — morning (account, risk tier + DQS, per-holding + SPY: overnight gap with STALENESS flag, regime, expected 5-day move, nearest levels), eod (today's decisions with reasons, day P&L, budget consumed), weekly (equity vs SPY with excess return, discipline counts incl. tier restrictions, facts_for_lessons + "never invent numbers" narration rule). Sections degrade gracefully with a `why` ("run sync daily"); T068/T076 gaps stated honestly in payload. `get_brief` tool (registry 15) + `GET /api/brief?type=morning|eod|weekly`. 6 seeded-db tests — 2026-08-13. Follow-ups → T062b.
- [x] T067 — DQS + graduated risk tiers, ENFORCED (`risk/tiers.py` + `risk/dqs.py`): budget-consumed ladder in the paper loop — tier 1 (≥25%): cost+RVOL floors doubled · tier 2 (≥50%): new-buy notional HALVED · tier 3 (≥75%): entries paused as no_trade · tier 4 (100%): the untouchable T033/T035 breaker; sells exempt at every tier; breaker PRECEDENCE preserved (tripped → loud gate rejection, not a quiet no_trade — tested). DQS v1: process-not-outcome score from signal_log (frequency vs guard, trading-into-drawdown, sizing CV, restraint counted free) — honest note that owner-fill scoring needs T036/T063 (→ T067b). `get_risk_status` tool (registry 14) + `GET /api/risk`. 15 hand-computed tests — 2026-08-13.
- [x] T077 — Expected-move & payoff distribution engine (`analysis/expected_move.py`): overlapping N-day return samples over trailing lookback → inclusive-interpolation percentile bands (p05..p95, return AND price terms), up_frac (historical hold-N win rate), median |move|, payoff ratio (None when a side is empty); VOL CLUSTERING via trailing-vol terciles — bands conditioned on the current tercile (quiet tape → narrower honest bands, proven in test); overlap-autocorrelation caveat + "NOT a forecast" in every reading. `get_expected_move` tool (registry 13) + `GET /api/expected-move/{symbol}`. 11 hand-computed tests — 2026-08-13. GARCH still deferred on evidence; v2 = T077b.
- [x] T054 — Range strategy + regime router (`backtest/strategies.py`): `make_range` trades only the lower `entry_frac` of the trailing range and REFUSES both trending AND unverifiable structure (`_regime_lite` returns up/down/none/UNKNOWN — the unknown state exists because an early bear is indistinguishable from an unknowable one; leak caught by the BEAR regime test, bars 39–44); `make_regime_router` = structure→momentum, checked-range→range, else CASH. Acceptance proven: router beats always-momentum in CHOP (momentum 0.0, router >100%), rides BULL, all-zero in BEAR. Registry: 6 templates — 2026-08-13. NOTE: closes-only regime-lite per D010 contract; volume-aware checks live in the loop (T055).
- [x] T055 — No-trade condition first-class (`backtest/paper_loop.py`): new `no_trade` signal_log action ("capital preserved by design"), buys-only (sells never blocked): overtrading guard (max_trades_per_day=5 across all symbols), ATR/price cost floor (expected-move proxy until T077), quiet-market check (full T050 classifier: RVOL < 0.3 AND bottom-quartile width). Tests: 6th-buy blocked, sell-still-allowed under guard, quiet fixture, dead-flat tape — 2026-08-13. Confluence-score threshold deferred to T077+backtest evidence per D017.
- [x] T052 — Intraday data + session analysis: `get_intraday_bars` (1Min…1Hour, tz-aware UTC starts, split-adjusted) + `analysis/intraday.py` — ET session grouping (zoneinfo, tzdata added for Windows; a 20:30-ET bar belongs to its ET day across UTC midnight), RTH filter (09:30–16:00, opt-out), cumulative session VWAP (typical price), VWAP crossings (churn detector), and TIME-OF-DAY RVOL — today's cum volume vs prior sessions by the same ET time, the doctrine's exact definition. `get_intraday` tool (registry 12) + `GET /api/intraday/{symbol}`. 12 hand-computed tests — 2026-08-13. Unblocks T075 confluence; the morning brief (T062) gets its "what kind of day is it so far" input.
- [x] T053 — Breakout detector (`analysis/breakout.py`): fresh-escape EVENTS (continuation bars never start one) with boundary, RVOL-at-break (thresholds shared with regime.py — one source of truth), hold-outside tracking, and a judged-once status taxonomy: confirmed (hold+volume) / failed (returned inside the hold window — the $100→$106→$99 fakeout, tested by name) / unconfirmed (held on weak volume — stay suspicious) / pending; `active` flag for live breaks. `get_breakouts` tool (registry 11) + `GET /api/breakouts/{symbol}`, D006 volume_feed label rides along. 9 hand-walked tests — 2026-08-13. Feeds T054 router + T056 exits.
- [x] T051 — Support/resistance levels (`analysis/levels.py`): swing highs/lows (shared `swing_points`, now public in regime.py) pooled + greedy price-proximity clustering (running mean, tolerance_frac) → levels with price (cluster mean), TOUCH COUNTS (min_touches=2 default — "one rejection is an event, two is a level"), provenance kind (support/resistance/MIXED — old floor becoming new ceiling is detected), signed distance, nearest support/resistance vs last close. Reachable: `get_levels` tool (registry 10) + `GET /api/levels/{symbol}`. 13 hand-walked tests incl. the mixed-kind breakdown fixture — 2026-08-13. Feeds T054 range strategy + T056 exit plans.
- [x] T078 — Vol-parity position sizing: `true_ranges`/`atr` (Wilder) in analysis/metrics + `risk/sizing.py` volatility_parity_notional (risk$ = equity × risk_per_trade_frac; ceiling = risk$/(stop_atr_multiple × ATR) × price); RiskLimits gains risk_per_trade_frac (default 1%, hard band ≤5%) + stop_atr_multiple (2.0). Paper loop applies to BUYS only (sells always reduce risk), logs a sizing note on bound orders, and FAILS CLOSED on <15 bars ("insufficient history for ATR"). Deliberate: sizer only shrinks; the engine's 20% cap still REJECTS loudly (no silent auto-resize). 12 new tests hand-computed (TR/ATR 22/9, ceiling 12.5k, whipsaw loop order 12.195 shares) — 2026-08-13.
- [x] T050 — Regime classifier (`analysis/regime.py`): trending_up/down · range_bound · breakout_watch from daily bars — swing-structure HH/HL (SMA-slope fallback for monotone series), 20-bar range + width percentile vs trailing windows (the coil), escape-vs-prior-range with suspected_fakeout on weak RVOL, per-label 3-signal confidence checklist (capped 0.9 — never certainty), volume_feed REQUIRED (D006). Shipped reachable: `get_regime` registry tool (9 tools now) + `GET /api/regime/{symbol}` so the owner can ask the Orb "what kind of market is SPY in?". 18 tests: doctrine fixtures (sawtooth trends, stationary triangle, coil, volume-confirmed breakout, fakeout) + hand-computed micros — 2026-08-13. Decision order doctrine: matured trend outranks its own escapes.
- [~] T097 — REVERTED 2026-08-14 (owner call): the particle FACE was iterated six
  times (voxel grid → sculpted 3D → holographic columns → microscopic rods →
  skull anatomy → green dots) and never reached a convincing likeness. Owner:
  "revert back to the orb". `apps/web/orb.html` restored to 5f77557 (the Orb
  with patience fixes) — no CDN dependency, voice loop untouched. LESSON worth
  keeping: procedural facial likeness is a poor fit for this codebase's
  verify-then-ship loop — each pass needed a human eye to judge, which is the
  one thing the gate can't automate. If a face returns, buy/commission the
  asset (a real head mesh or a point-cloud scan) instead of sculpting it in
  gaussians. Face-era work preserved in git history (8fc9927..82b3a85).
- [x] T097 v2 — Sculpted 3D face (superseded, then reverted — see above):
  continuous gaussian-feature depth field tuned via offline renders, ~12k WebGL
  points (three.js CDN, additive), shader-driven cursor-follow / pupil-lead /
  lip-sync / shimmer / edge-dissolve, 3/4 rest pose per reference — 2026-08-14.
- [x] T097 — The KUBERA Face (owner request 2026-08-14, reference image: voxel head
  dissolving into a particle network): the Orb canvas now renders a procedurally
  generated depth-mapped voxel face — no assets, no libraries, ~1,300 particles
  from two-ellipse silhouette + feature carving (brow/sockets/pupils/nose/lips/
  chin), verified by offline render before shipping. Head yaw/pitch FOLLOWS THE
  CURSOR (smoothed, ±0.55/±0.32 rad), pupils lead the turn with extra gain, idle
  gaze wanders after 4s without mouse. Mouth voxels ride the real TTS amplitude
  (S.amp) when speaking; thinking = violet shimmer; left edge dissolves into a
  drifting wireframe halo per the reference. Same canvas id, click contract,
  state machine, and voice loop as the orb it replaced — zero logic touched —
  2026-08-14.
- [x] T073 — The KUBERA Orb (`apps/web/orb.html` at GET /): voice-first web UI — breathing orb (idle gold / listening teal / thinking violet / speaking amplitude-reactive), browser SpeechRecognition STT, streaming `GET /api/tts` (edge-tts, lazy server dep w/ actionable 503), tool-call chips per reply, typed fallback, "confirm this turn" checkbox as the deliberate gesture; 4 tests (route + fake-edge streaming) — 2026-08-12. Phase 5 opened early per D015. Zoey-grade latency = T074.
- [x] T061 — Investment Policy Statement: `investment_policy` table (migration `08dfc64f8e4b`) + `data/ips.py` (partial upsert, lists replace wholesale, compact prompt block), injected into every chat system prompt; tools `get_ips` (free) + `update_ips` (**requires_confirmation** — first gated tool live: "KUBERA, set my max drawdown to 15%" → asks → you confirm deliberately); `GET /api/ips`; guard test now asserts gated set == {update_ips}; 10 new tests — 2026-08-12
- [x] T070 — Push-to-talk voice loop (code-complete; owner acceptance = T071): `api/voice_loop.py` tested orchestration (conversation threading, silence never reaches KUBERA, typed-only confirm passthrough) + `scripts/talk.py` (sounddevice capture, STT: faster-whisper local / OpenAI fallback, TTS: SAPI / edge-tts, voice=true wired), requirements-voice.txt keeps audio deps out of CI — 2026-08-12
- [x] T046 — Claude Agent SDK provider (`api/llm_claude_sdk.py`, D012): chat on the owner's Max subscription; registry bridged as SDK tools with locked permissions (mcp__kubera__* only, no Bash/files, dontAsk, bounded turns); confirmation gate + audit trail preserved via side-channel events the chat loop persists; policy verified via claude-code-guide agent (personal-use-only); optional dependency with actionable errors; 7 fully-mocked tests — 2026-08-11. Owner activation = T047.
- [x] T044 — Context budgeting (`api/context.py`): block-wise selection (assistant+tool-results indivisible — provider contracts never break), oldest exchanges drop whole, newest always kept, old tool payloads elided while assistant conclusions survive; KUBERA_CONTEXT_BUDGET_CHARS setting (default 24k chars ≈ 6k tokens); 8 tests incl. pairing-never-split across budgets — 2026-08-11. (Research-memory retrieval deferred to Phase 7's vector store per D007.)
- [x] T043 — Conversation safety rails: `requires_confirmation` per tool + ConfirmationRequiredError (ctx.confirmed set ONLY from ChatRequest.confirm — the model can never self-confirm), guard test that no current tool requires confirmation, recency post-check appending a deterministic asof footer when a data-grounded reply lacks a date; 8 new tests incl. full two-turn confirmation flow — 2026-08-11
- [x] T042 — POST /api/chat: bounded conversation loop (persona + history → LLM → registry tools → grounded answer), conversations/chat_messages tables + migration `7bb8528ec2d3`, every message/tool-call/result persisted with timestamps, tool errors surfaced verbatim, GET /api/chat/{id} audit view; 7 scripted-provider tests + endpoint E2E — 2026-08-11
- [x] T041 — LLM abstraction (`api/llm.py`): neutral message/tool format, Anthropic + OpenAI adapters (thin httpx, no SDKs), both-direction translation tested via captured wire payloads, build_provider fail-fast selection (LLM_PROVIDER env; Gemini = future add); settings: ANTHROPIC/OPENAI keys + model overrides — 2026-08-11
- [x] T040 — Persona (`api/persona.py`): build_system_prompt with 8 non-negotiable CORE_RULES (tools-only numbers, recency, no certainty, paper clarity, confirm-before-capital, can't override risk engine, no gap-filling, not-an-advisor) + analyst voice; guard tests prevent silent rule deletion — 2026-08-11
- [x] T034 — Backtest results ledger: `backtest_runs` table + migration `33592ebf6de6`, `backtest/ledger.py` (record/list/run_and_record), shared TEMPLATES + build_strategy, `GET /api/backtests` + `POST /api/backtests/run`, `run_backtest` registry tool (6 tools now); tests incl. StaticPool fix for cross-thread in-memory SQLite — 2026-08-11. **Phase 3 core complete** (T036 polish optional).
- [x] T035 — Risk-state persistence: `risk_state` table + migration `35b6c01bf49b`, `engine.restore()` (persistence-only), `risk/persistence.py`, paper-loop restore/persist hooks, `scripts/risk_reset.py` (note-required, type-RESET confirm); killer test: restarted loop loads tripped breaker from DB and stays blocked — 2026-08-11
- [x] T032 — Paper-trading loop: `backtest/paper_loop.py` (strategy → risk gate → paper order → SignalLog audit row for every decision incl. rejections/no-action), `place_order` on AlpacaClient (paper-only by construction), `signal_log` table + migration `c09d9671853d`, `scripts/paper_trade.py` CLI; 10 new hand-computed tests incl. breaker-blocks-second-cycle — 2026-08-11
- [x] T031 — Strategy library: make_momentum (trailing-return trend filter) + make_mean_reversion (band-below-SMA dip buyer, stateless), validated params; hand-tracked equity tests + regime proofs (momentum flat through the whole synthetic bear; MR profits in chop, sits out smooth bulls) — 2026-08-11
- [x] T033 — Risk engine v1 (`risk/engine.py`, spec §8): fail-closed pre-trade gate, per-symbol position cap (inclusive), daily-loss circuit breaker (trips at limit, blocks buys AND sells, survives recovery and new days, manual reset only), timestamped decisions with all violated rules + numbers; 22 hand-computed tests — 2026-08-11
- [x] T030 — Backtest engine v1 (`backtest/engine.py` + `strategies.py`, per D010): no-lookahead by construction (prefix-enforced, tested), cost model in bps, weight validation, metrics from analysis layer; buy-and-hold + SMA-cross templates; 8 hand-computed tests — 2026-08-11
- [x] T017 — Chore: shared httpx plumbing extracted to `data/_http.py` (build_client + checked_get); both clients refactored, error text byte-identical, same 85 tests green — 2026-08-11
- [x] T025 — Symbol briefing composer (`analysis/briefing.py` + `sma()` in metrics): trailing 20/60/252d returns, 60d ann vol, 252d max DD, 52-week high/low distance, SMA50/200 trend context, owner's exposure; graceful degradation on thin history; `get_symbol_briefing` tool + `GET /api/briefing/{symbol}`; 12 new tests — 2026-08-11
- [x] T024 — Tool-calling registry (`api/tools.py`, spec §3): typed pydantic-validated tools with JSON-schema export (`GET /api/tools`), context injection, clear error taxonomy; 4 tools registered (get_portfolio, get_latest, get_daily_bars, compare_benchmark); 8 tests — 2026-08-11
- [x] T022 — Win/loss breakdown: `analysis/portfolio.win_loss()` (winners/losers/flat, natural-sign gain/loss sums, best/worst), surfaced in `/portfolio` as `win_loss`; hand-computed tests — 2026-08-11
- [x] T021 — Benchmark comparison: `analysis/benchmark.py` (inner-join date alignment, normalized curves, per-series metrics, excess return), `data/history.py` equity_history (last snapshot/day/account, summed), `GET /api/benchmark?symbol=SPY&days=90` with actionable 409/503; 9 new tests — 2026-08-11
- [x] T020 — `analysis/metrics.py`: daily_returns, cumulative_return, CAGR, volatility, Sharpe, max_drawdown_frac — documented conventions (252 ppy, positive-magnitude drawdown, ValueError on bad input), 16 known-answer tests hand-computed — 2026-08-11
- [x] T015 — `GET /portfolio`: live account + positions at request time, totals/weights/returns via `analysis/portfolio.summarize()` (deterministic, tested); 7 new tests. **Phase 1 code-complete** — owner sign-off via T007 — 2026-08-11
- [x] T014 — Snapshot sync job: `data/sync.py` (idempotent account upsert + account/position snapshot writes), `scripts/sync.py` CLI (one-shot / `--loop N`), account model gains `external_id`; idempotency tests — 2026-08-11
- [x] T013 — DB schema v1: SQLAlchemy 2 models (broker_accounts, account_snapshots, position_snapshots, transactions), UTCDateTime type rejecting naive datetimes, engine/session factory, first alembic migration `bee2b4896cdf` + migration-parity test; `alembic -c backend/alembic.ini upgrade head` — 2026-08-11
- [x] T012 — Market data client (`backend/data/market_data.py`): latest trade/quote + daily OHLCV (IEX free feed, split-adjusted), dual timestamps (exchange_ts + asof) on every payload, RFC3339 parser handling Alpaca's variable-precision fractions on py3.10+; `GET /api/market/{symbol}/latest` + `/bars`; 9 new tests — 2026-08-11
- [x] T011 — Alpaca paper client (`backend/data/alpaca.py`): account + positions, timestamped/sourced payloads, actionable 401s, **live-endpoint refusal rail** (§7.4 not implemented = no code path to real money); `GET /api/account`; 8 new tests + skip-guarded live integration test — 2026-08-11
- [x] T010 — Typed settings loader (`backend/settings.py`, pydantic-settings): fail-fast `require_alpaca()`, SecretStr, `/health` reports config state; 5 tests — 2026-08-11
- [x] T004 — git init, CI workflow, gitleaks pre-commit config, .env.example, .gitignore — 2026-08-11
- [x] T003 — Backend skeleton: FastAPI /health, analysis.returns + 7 tests, ruff, verify.py — 2026-08-11
- [x] T002 — project-memory working files (TASKS, DECISIONS, ISSUES, PROGRESS) — 2026-08-11
- [x] T001 — AGENTS.md + PROJECT_SPEC.md authored — 2026-08-10
