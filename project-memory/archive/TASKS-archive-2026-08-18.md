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


# Section added 2026-08-19 by curation session (D031)
# Moved from TASKS.md 'Awaiting review': all REVIEWED DONE blocks
# (T083b, T083b-probe, T083, T066, T067b, T023b, T016b, T113, T016c, T112)

- **T083b (EDGAR earnings history — free, keyless, probed) — DONE 2026-08-18
  (Claude/Cowork; REVIEWED by Gemini/Antigravity — PASS at 634d20c)**. Owner's probe: ALL GREEN — 10,387 tickers in
  the CIK map, 46 earnings 8-Ks (~11yr) for the probe symbol back to 2015,
  46/46 with acceptance timestamps. Built against exactly that shape:
  (1) settings: edgar_contact (SecretStr — the SEC-required UA contact,
  never logged; repo is public) + edgar_base_url/edgar_www_url (T107
  convention). (2) data/edgar.py EdgarClient — two endpoints only:
  company_tickers.json (fetched once per client, cached) and submissions
  JSON (columnar arrays, item-2.02 filter, zero-padded CIK path pinned in
  test); named errors for 403 (UA problem), 429 (do not retry), unknown
  ticker (ETFs have no CIK); unparseable filingDate → reported, never
  guessed (T102). (3) hint_from_acceptance in analysis/event_rates.py — the
  REAL filing clock replaces bmo/amc guesses: ≥16:00 ET = amc (next bar),
  else bmo; zone via MARKET_TZ so EDT/EST flips itself; naive datetimes
  refused. (4) get_event_base_rates: EDGAR history feeds the SAME
  earnings_observed store (source=sec-edgar; dedupe + enrichment already
  built in T083) — merging IS the store; any EdgarError degrades to a named
  note and the store still answers. (5) ToolContext gains edgar; wired
  best-effort in main.py chat AND mcp_server — which CLOSED A PRE-EXISTING
  GAP: the chat endpoint built NO fred/fmp at all, so calendar/macro tools
  claimed "not configured" over chat even with keys present. (6) T106
  audit: close_tool_context's fixed member list would have LEAKED fmp/edgar
  per MCP call — caught in self-review, list extended with the why comment.
  EVIDENCE (D027): 9 tests in test_edgar.py — probe-faithful columnar
  fixture (the owner's real 20:30:28Z sample asserted amc), item-2.02
  filtering (10-Q and 5.02 8-K excluded), UA-carries-contact asserted on
  every request, zero-padded CIK path, named 403/unknown-ticker refusals,
  fail-closed bad dates, DST clock cases (20:30Z July=amc / January=bmo),
  naive refusal, end-to-end tool run (4 8-Ks → store rows source=sec-edgar,
  hints amc, timing_assumed all False, rates computed) + EDGAR-500 degrade;
  15/15 with store suite; 22/22 with mcp_server; ruff clean; pyrefly
  exactly 1; full gate PASS.
  D028 objections: (a) recent-window only — paged archive files for >11yr
  history are an UNOBSERVED shape, deliberately not fetched (noted in
  docstring); (b) EDGAR dates carry no estimates so beat/miss stays
  "unknown" for EDGAR-only rows — the MOVES are the core of the question
  and need none; FMP-stored estimates enrich rows where dates coincide;
  (c) company_tickers.json has no ETFs — get_event_base_rates on SPY will
  say so via the named unknown-ticker error path; index-fund earnings
  don't exist, so this is correct, but the message is worth the reviewer's
  read; (d) chat context now constructs up to 3 extra clients per request —
  each is lazy/cheap (no network until used), matching the brief endpoint's
  established pattern.
  Owner: nothing to do — EDGAR_CONTACT is already in your .env from the
  probe. Ask KUBERA "should I hold NVDA through earnings" and years of
  history answer immediately.
- **T083b probe (scripts/edgar_check.py) — DONE 2026-08-18
  (Claude/Cowork; REVIEWED by Gemini/Antigravity — PASS at 8e15153)**. The gate on T083b, built per D030/D034: a keyless probe
  the owner runs where KUBERA lives (sandbox cannot reach sec.gov —
  demonstrated: ProxyError → UNREACHABLE → named skip, exit 1). Measures:
  ticker→CIK mapping (company_tickers.json), one company's submissions JSON
  (8-K count, whether `items` truly carries "2.02", filingDate depth),
  acceptanceDateTime presence — a REAL clock that would upgrade T083's
  bmo/amc timing convention from assumed to KNOWN — and SEC etiquette
  (declared UA, 0.2s spacing under the ~10/s ceiling). Statuses/counts and
  three date-only samples; explains what each line decides.
  PII DISCIPLINE (D028 self-catch): my first version embedded the owner's
  personal email in the committed UA string — the repo is PUBLIC, so the
  contact now comes from .env (EDGAR_CONTACT, added to .env.example);
  without it the probe REFUSES (exit 2) with the one-line fix, and the
  contact is never echoed in output. Same rule as masked account numbers.
  EVIDENCE (D027): ruff clean; refusal path run (exit 2, actionable);
  sandbox run demonstrates the named-unreachable path; gate PASS. No
  backend code exists yet — that is the point: the probe's table decides
  the T083b build (owner action: add EDGAR_CONTACT to .env, run
  `python scripts\edgar_check.py`, paste the table).
- **T083 (event reaction base rates — D019) — DONE 2026-08-18 (Claude/Cowork; REVIEWED by Gemini/Antigravity — PASS at 531ea20)**. "Should I hold through earnings" answered from the
  symbol's own bars as BASE RATES — the note in every payload says
  "description of the past, not a prediction". Built:
  (1) analysis/event_rates.py (pure) — per past earnings date: event-day
  move with the TIMING CONVENTION written down (amc reports move the NEXT
  bar; bmo its own; missing hints default to bmo AND are counted in
  timing_assumed — an invisible wrong-day booking would smear every number),
  next-day follow-through, 5-bar pre-event runup (the D019
  "priced-for-perfection" ingredient); beat/miss from eps_actual vs
  eps_estimated ONLY — never inferred from the price move (circular);
  splits carry n, median event move, closed-down count (the "6 of 8 beats
  still closed down" shape), median next-day; <4 measurable events →
  insufficient_history ("anecdotes are how superstitions start");
  events outside bar history land in `unmeasured` with why, never dropped.
  (2) fmp.py EarningsEvent gains eps_actual passthrough (None on future/
  absent — unknown split, never guessed). (3) get_event_base_rates tool
  #39 (guard bumps 38→39 x4 + name-set): one calendar request for the whole
  window (250/day respected), market_today() bounds (T111), named errors
  when FMP absent or the symbol has no past dates. (4) fmp_check.py gains a
  PAST-window calendar probe row — historical dates + epsActual are the
  unprobed shape here (the 08-17 probe asked only a future window); the
  D030 pattern: fail-closed code now, owner's probe answers definitively.
  EVIDENCE (D027): 9 tests, every move hand-computed on tiny tapes — bmo
  110/109-1 with runup 109/104-1; amc shifting to the next bar; Saturday
  event rolling to Monday with timing_assumed counted; the beats-that-
  closed-down split (2 of 2 on a falling tape); MIN_EVENTS refusal;
  out-of-history events reported; last-bar event has next_day None; short
  history runup None; alignment/ascending validation. 39 tool-count tests
  green; ruff clean; pyrefly exactly 1; full gate PASS.
  D028 objections: (a) MY OWN BUILD BUGS, both caught before commit: the
  ascending-dates guard was INVERTED (rejected every valid series — caught
  reading my own diff before first test run), and two assertions needed
  abs tolerance for the module's 6dp rounding; (b) the free tier's PAST
  calendar + epsActual availability is fixture-believed, not probe-verified
  — the tool fails with a NAMED error pointing at the new probe row if the
  owner's tier answers differently; (c) "inline" (actual == estimate) is
  its own split rather than a beat — a defensible alternative buckets it
  with beats; chosen and documented; (d) reaction-day close-over-close
  ignores the OPEN gap — gap-and-fade days read as small moves; daily bars
  cannot separate the gap without opens threaded through, noted as a
  future enrichment, not silently approximated.
  OWNER PROBE ANSWERED (2026-08-18, same session): **past calendar windows
  PAYWALLED** on his tier — the forward window answers, history does not.
  REDESIGNED against the measurement (build delta, new SHA):
  (1) earnings_observed table (alembic 9d1c5b3fa284, revises 4f8e2a917c66,
  single head) — every forward-window fetch RECORDS what it saw BEFORE it
  happens; dedupe per (symbol, event_date); a later fetch carrying
  eps_actual/hint BACKFILLS the row (reports linger in the visible window
  briefly after they land). (2) data/earnings_store.py: record_events /
  record_calendar (best-effort BY CONTRACT — returns 0 on any failure,
  never breaks a brief) / stored_events. (3) get_event_base_rates now reads
  PAST events from the store, fetches ONLY the forward window (the probe-
  verified shape — no paywalled request is ever made), and feeds the store
  on every call; empty store → named error explaining the paywall reality
  and that history accumulates as quarters pass. (4) morning brief's
  earnings section + get_earnings_calendar tool also feed the store — three
  growth paths. The past assembles itself; base rates go live once 4+
  observed dates for a symbol have passed.
  DELTA EVIDENCE: 6 new tests in test_earnings_store.py (dedupe +
  actual-backfill, best-effort never raises, ordering, tool-from-store
  without FMP, empty-store paywall-naming error, forward fetch feeding the
  store with future dates) + the 9 event_rates tests unchanged; migration
  applies on scratch DB; ruff clean; pyrefly exactly 1 after annotating
  fetch_note (canary caught the dict-literal inference again); gate PASS.
  DELTA D028: the store tests EXPOSED A LATENT BUG in the first commit —
  DailyBar.date is a "YYYY-MM-DD" STRING and my str-vs-date comparison
  would have crashed the tool on its first real run; fixed and the
  conversion commented. Follow-up filed as T083b (below): SEC EDGAR 8-K
  dates as the fast-history option — free, no key, authoritative — gated
  on its own probe per D030.
  REVIEWED 2026-08-18 by Gemini/Antigravity — PASS (covering commit 531ea20 per D033)
    aligned: Provides deterministic event reaction base rates from bars (event-day move with amc/bmo timing convention, next-day follow-through, 5-bar runup, beat/miss/inline splits from eps_actual vs estimate without circular price inference); adapts gracefully to FMP free tier paywall on past calendar windows by accumulating forward events into `earnings_observed` table (Alembic 9d1c5b3fa284) across briefing and tool calls.
    checked: Validated commits 8e8b00d + 531ea20: (1) `backend/analysis/event_rates.py` pure computation with MIN_EVENTS=4 floor and unmeasured event logging; (2) `backend/data/earnings_store.py` best-effort upsert and backfill logic with `earnings_observed` model; (3) `get_event_base_rates` tool #39 wiring with DailyBar date string conversion and tool count guards (38->39); (4) 9 tests in `test_event_rates.py` and 6 tests in `test_earnings_store.py` pass; (5) single Alembic head `9d1c5b3fa284`; (6) full `scripts/verify.py` green (953 passed, ruff clean, memory budgets within bounds).
    concerns: none
- **T066 (trade coaching: pre/post-trade reviews, persisted — D014) — DONE 2026-08-18 (Claude/Cowork; REVIEWED by Gemini/Antigravity — PASS at 1f6014c)**. Composition, not new math —
  the coaching layer judges a trade against modules that already exist.
  Built: (1) analysis/coaching.py (pure) — compose_pre_trade_review: a
  CHECKLIST (not a composite score — a single number would launder judgement
  into false precision) over six sections, each ok/attention/missing WITH its
  reason: thesis+invalidation ("without 'what proves me wrong', an exit is an
  emotion"), IPS fit (restrictions are HIS written rules), concentration
  (post-trade weight; attention at 15%, the engine's 20% cap named — friction
  before the breaker, the T067 idea), regime fit (buying trending_down =
  attention; breakout_watch = coil caution), pattern history (T104's verdict
  passed through with sample sizes), exit-plan presence. Absent inputs land
  MISSING naming their supplier tool — an unattempted check is surfaced,
  never skipped (I026 generalised). compose_post_trade_review: trip vs the
  T063 journal row — horizon adherence (winner exited <25% of horizon = the
  cut-winners tell; loser held >2x = "a thesis past its clock"), levels on
  record (qualitative — attribution trips carry no exit PRICE, stated
  honestly), followed/overridden (marked = ok either way; UNMARKED =
  attention), facts_for_lessons lines only. An unjournaled trade IS the
  finding. (2) trade_reviews table (alembic 4f8e2a917c66, revises
  7c3a91e0d5b2, single head) — 'pre' rows freeze the checklist BEFORE entry
  so hindsight cannot rewrite it. (3) ONE tool coach_trade (#38, mode
  pre|post; guard bumps 37→38 in test_tools x2 / test_chat / test_claude_sdk
  + name-set): pre gathers best-effort (IPS, account+position, regime via
  classify_regime, pattern via evaluate_pattern_warnings on DB fills) and
  persists; post picks the most recent closed trip for the symbol from the
  SAME DB->attribution path T069/T067b use, joins the latest journal row
  at-or-before entry, persists with journal_id.
  EVIDENCE (D027): 14 tests — all-ok full-input case (6 ok, weight 5%);
  the dangerous-combination case (5 attention + 1 missing: no invalidation,
  IPS-restricted, 25% cap breach, buying a downtrend, pattern warning, no
  exit plan); concentration boundaries hand-computed (16% attention / 10% ok
  incl. existing position); missing-inputs name their suppliers; post-trade
  cut-winner (2 of 10 days) and loser-past-clock (25 vs 10) flagged;
  unjournaled-is-the-finding; unmarked-flagged-override-free; end-to-end
  tool runs persisting TradeReview rows (pnl +100 = 10x(110-100), journal_id
  joined); regime path with VALID bars; failed regime read NAMES the error.
  Migration applies on scratch DB (all columns). ruff clean; pyrefly exactly
  1; full gate PASS.
  D028 objections: (a) the canary caught a REAL bug my tests missed —
  reading.label vs .regime, on the only path no test covered (market
  present); fixed, then BOTH sides pinned: valid bars exercise the line,
  and a crashing read now reports "FAILED (ValueError: ...)" instead of my
  original broad-except pretending the check was never attempted; (b)
  coach_trade WRITES TradeReview rows and is exposed via MCP like
  record_decision — same class (no capital, no rails); reviewer should
  confirm agreement with the T045 read-only philosophy; (c) correlation
  (T079) is NOT a section — a full overlap check per review costs a quote
  fetch per holding; the persona already orders get_correlation before
  buys, noted rather than duplicated; (d) post-mode matches journal rows
  by symbol+time only — a same-symbol re-entry within the window could
  join the wrong row; deterministic rule documented, refinement cheap if
  it ever misleads.
  REVIEWED 2026-08-18 by Gemini/Antigravity — PASS (covering commit 1f6014c per D033)
    aligned: Implements pre/post trade coaching with a 6-section checklist (thesis+invalidation, IPS fit, concentration friction at 15%, regime fit, T104 pattern history, exit-plan presence) and post-trade adherence checks against T063 decision journal rows; persists to `trade_reviews` table via single-head migration 4f8e2a917c66 and exposes coach_trade tool #38 with proper guard bumps.
    checked: Validated commit 1f6014c: (1) `backend/analysis/coaching.py` pure composition for pre and post-trade reviews with explicit section statuses and supplier naming on missing inputs; (2) `trade_reviews` table model and Alembic migration `4f8e2a917c66` (single head verified); (3) `coach_trade` tool registration (#38) and guard count bumps in `test_tools.py`, `test_chat.py`, `test_claude_sdk.py`; (4) 14 unit and tool integration tests in `test_coaching.py` pass; (5) full verify gate `scripts/verify.py` green (938 passed, ruff clean, memory budgets within bounds).
    concerns: none
- **T067b (DQS v2 — score the OWNER's own trading) — DONE 2026-08-18 (Claude/Cowork; REVIEWED by Gemini/Antigravity — PASS at fdfe6e9)**. v1 scored the paper loop and said so; both of
  its stated prerequisites (broker-fill sync, decision journal) have landed,
  so v2 scores HIS record. Built backend/risk/owner_dqs.py (pure):
  (1) disposition_effect (≤30) — median winner hold vs median loser hold;
  ratio < 1 = cutting winners while riding losers; refuses under 5 trips on
  EITHER side, and a zero loser-median (all same-session) yields no verdict
  rather than a divide-by-zero opinion; (2) revenge_sizing (≤30) — reuses
  T069's sizing_drift VERBATIM so the codebase has one definition of the
  revenge pattern, not two that drift; (3) journal_discipline (≤20) — only
  the UNMARKED share costs; overriding KUBERA is explicitly not penalised
  (his judgement is why the journal exists); (4) budget_from_ips() — converts
  his ratified max-drawdown into an implied daily budget by T069's own
  1/3 convention, prints it beside the ENFORCED limit and flags disagreement,
  as a PROPOSAL that never applies itself (a safety rail that moved on its
  own would be the "talked out of the lockout" failure the tiers exist to
  prevent). FOMO-into-late-RVOL is NOT built and says why in every report:
  statement fills are date-only, so it would be guesswork (T102).
  Wiring: get_risk_status gains an `owner_dqs` block sourced from DB
  Transactions -> attributed_fills_from_rows -> fifo_attribution — the SAME
  path T069 uses, so the two behavioural reads cannot disagree about what a
  round trip was; empty table degrades to a note pointing at sync.py. No new
  tool, so no guard-count bump.
  EVIDENCE (D027): 14 unit tests hand-computed (0.25 ratio -> 45 capped to
  30; 0.75 -> 15.0; winners-held-longer free; sample-floor refusal; undated/
  negative/scratch trips skipped not defaulted; same-session no-verdict;
  revenge ratio 2.0 -> capped 30; unmarked 5/10 -> 10.0; IPS 15%/3 = 5% vs
  enforced 2% flagged looser) + 2 end-to-end through the tool on a seeded DB
  (10 real Transactions -> 10 trips -> ratio 0.25 -> score 70.0; empty DB ->
  available:false naming sync.py). 36 passed across both suites; ruff clean;
  gate PASS.
  D028 objections: (a) MY OWN CANARY CAUGHT ME — the pyrefly count went 1 -> 2
  on a dict literal that inferred `agrees: None`; re-measured (a transient
  fooled me once before), confirmed reproducible, fixed with an explicit
  annotation, back to exactly 1; (b) T069's sizing_drift compares raw
  qty x price, so option notionals are understated 100x — it cancels in the
  RATIO unless the option/equity MIX differs between post-loss and post-win
  buys; I did not change a shared T069 function inside this ticket, and the
  reviewer may reasonably want that as its own; (c) the disposition penalty
  slope (60x the gap) and the IPS 1/3 convention are chosen tunables, both
  commented; (d) held_days comes from attribution, which reads date-only
  statement-sourced rows as whole days — the metric is real but coarse until
  time-stamped Schwab fills accumulate.
  REVIEWED 2026-08-18 by Gemini/Antigravity — PASS (covering commit fdfe6e9 per D033)
    aligned: Implements DQS v2 for the owner's real trading record across disposition effect, revenge sizing (reusing T069 definition), journal discipline (unmarked decisions penalized, overrides allowed), and IPS-implied budget proposal (pure advisory), while explicitly refusing guesswork on FOMO-into-late-RVOL until intraday timestamps accumulate (T067c).
    checked: Validated commit fdfe6e9: (1) `backend/risk/owner_dqs.py` pure scoring functions with sample floor checks, median zero hold protection, and capped penalties; (2) `backend/api/tools.py` wiring `_owner_dqs_block` into `get_risk_status` using the verified DB -> attribution pipeline; (3) 14 hand-computed unit tests in `test_owner_dqs.py` and 2 tool integration tests in `test_dqs_tiers.py` pass; (4) full `scripts/verify.py` green (924 tests passed, 0 lint errors, memory budgets all within bounds).
    concerns: none
- **T023b (fundamental ratios from FMP statements — D030 #4) — DONE 2026-08-18 (Claude/Cowork; REVIEWED by Gemini/Antigravity — PASS at 8609e54)**. Built:
  (1) backend/analysis/fundamentals.py (NEW, pure, no I/O) — FCF per fiscal
  year with the T016c principle applied to statements: the statement's OWN
  freeCashFlow is preferred ("reported"), else derived OCF + capex where FMP's
  capex is a NEGATIVE outflow; a POSITIVE capex is an unobserved sign
  convention → the year lands in unparsed, never silently "fixed" (T102).
  FCF yield = latest fiscal FCF / TODAY's market cap, with the backward-
  numerator/live-denominator note; debt/equity SUPPRESSED (None + why) when
  equity is non-positive — a negative ratio reads as "low debt", the exact
  wrong conclusion; debt/assets separately; STALENESS_NOTE in every reading.
  (2) data/fmp.py gains cash_flow_statement (probe-verified), balance_sheet
  (NOT probe-verified — named FmpError on paywall), profile_market_cap
  (probe-verified; None when payload lacks a usable number). (3) briefing
  tool gains a fundamentals block: None without ctx.fmp; FmpError on the
  cash-flow half → available:false with why; a paywalled balance sheet must
  NOT cost the FCF half (pinned in test). (4) scripts/fmp_check.py gains the
  balance-sheet probe row so the owner's next run answers the one endpoint
  the 2026-08-17 probe missed.
  EVIDENCE (D027): 24 tests across test_fundamentals (6, all hand-computed:
  80k/1.6M = 5% yield, 50k/200k = 0.25 D/E, derived 100k−25k = 75k,
  positive-capex refusal, negative-equity suppression, unparsed reporting) +
  test_fmp (+3: fetchers, named paywall, non-list shape refusal, unusable
  profile → None) + test_briefing_tool (+3: null without fmp, hand-computed
  block with fmp, paywalled-balance-sheet survival). ruff clean; pyrefly
  exactly 1 (I023 canary); full gate PASS.
  D028 objections: (a) fixture rows follow FMP's DOCUMENTED statement shape —
  same honesty note as T023 v1; fail-closed unparsed reporting is the
  mitigation and the owner's next briefing run is the live proof; (b) FCF
  yield mixes a fiscal-year numerator with a live denominator — the only
  option without paid TTM data, and the note says so in every payload; (c)
  no income-statement fetch = no margins/EPS — deliberate scope hold (ticket
  names FCF + debt), one request cheaper per briefing on a 250/day budget.
  OWNER PROBE RUN 2026-08-18 (same session): **balance sheet OK (1 row)** —
  debt ratios are LIVE on his tier, no code change needed (the briefing was
  built to light up when the endpoint answers). Full table also corrects one
  stale record: analyst estimates now reads OK (1 row) — the 08-17 "HTTP 400"
  was MY probe's parameter bug, fixed in T023 v1; the endpoint answers on the
  free tier. Estimate FEATURES stay out of KUBERA regardless until a ticket
  argues them in — availability ≠ adoption; estimates are third-party
  opinions (D019/D030 discipline). news/transcripts confirmed paywalled,
  D030's source decisions unchanged. Remaining owner check: one briefing
  with FMP_API_KEY set → fundamentals block, unparsed == [].
  REVIEWED 2026-08-18 by Gemini/Antigravity — PASS (covering commit 8609e54 per D033)
    aligned: Brings deterministic FCF yield and debt ratios from annual statements into the symbol briefing with fail-closed sign validation and explicit staleness labeling, keeping within the 250 req/day free budget (D030).
    checked: Validated commit 8609e54: (1) `compose_fundamentals` in `backend/analysis/fundamentals.py` hand-computed math (80k/1.6M = 5% yield, 50k/200k = 0.25 D/E, 100k-25k derived = 75k FCF), negative equity debt/equity suppression ("a negative ratio reads as low debt"), and positive-capex unparsed reporting; (2) `data/fmp.py` statement fetchers and profile market cap; (3) briefing tool fundamentals block and paywall/error graceful degradation paths; (4) owner ran `python scripts/fmp_check.py` on live key confirming balance sheet OK (1 row), cash flow OK (5 rows), income statement OK (5 rows), profile OK. Ran `pytest backend/tests/test_fundamentals.py backend/tests/test_fmp.py backend/tests/test_briefing_tool.py` (24 passed) and full `verify.py` (908 passed, ruff clean, memory budgets all within bounds).
    concerns: none
- **T016b (automated API-vs-statement cross-check) — DONE 2026-08-18
  (Claude/Cowork; REVIEWED by Gemini/Antigravity — PASS, third verdict,
  explicitly covering delta fixes 71670b2 + 545f84b; owner acceptance CLEAN
  39/39 exit 0)**. Fully closed: Gemini's final verdict cites the post-fix
  evidence (896 tests, DST window edges 05:00Z/04:00Z, both CLI wirings, the
  owner's clean run) — current as of the last code commit on this ticket.
  D033 RECORDED off this ticket's two review races (verdicts at 16:08 and
  16:18 each went stale within minutes; the second's own evidence — "38
  orders", 893 tests — proved it predated 545f84b): from now on a verdict
  names the SHA it covers, the reviewer confirms it is still the newest
  commit on the ticket's files before signing, and SHA-less verdicts are
  void under D027. Propagated to REVIEW.md §4 + docs/agent-briefs.md.
  Two independent sources agreeing, not a machine agreeing
  with itself; the human tick-off keeps the final word. Built:
  backend/analysis/cross_check.py (pure, no I/O) + scripts/cross_check_schwab.py
  (CLI: live pull + parse_directory(private/), prints MATCHED / API-ONLY /
  STATEMENT-ONLY in full, exit 0 only when clean, SchwabError → named
  "SCHWAB UNAVAILABLE" note, read-only). Join design from the owner's own
  March verification: API executions aggregate BY (order_id, symbol, side)
  with qty-weighted price (his 71+29=100 @ 0.21 to-the-penny case is THE
  fixture); OCC symbols ("NVDA  260320C00177500") normalise to the statement's
  underlying+expiry/right/strike key, fail-closed (unparseable OCC → reported,
  never guessed into an equity match); API UTC times join on their
  America/New_York date (T111). Match = same ET date + instrument key + side +
  qty, price within ±0.01 default (weighted avg vs statement rounding). Greedy
  1:1 within groups — two identical orders need two statement lines. NEVER
  silently reconciles: near-misses (price-out-of-tol same day, or dates ≤3d
  apart with price OK) are labelled notes; the lines stay unmatched. Fee
  comparison (both sides carry broker numbers post-T016c/T108b) is
  informational only, never affects matching.
  EVIDENCE (D027): test_cross_check.py 14 tests, all hand-computed — the
  71+29 case, weighted-avg 0.206 vs printed 0.21 inside tol, 23:30 UTC staying
  on its ET day, both-only buckets, near-miss labels, greedy pairing,
  fail-closed OCC, fee notes, qty/tol validation. Live CLI run in sandbox:
  named degradation confirmed ("SCHWAB UNAVAILABLE", exit 2 — api.schwabapi.com
  unreachable here per I002; the full path needs the owner's machine). ruff
  clean; pyrefly exactly 1 (I023 canary); full gate PASS.
  OWNER RUN #3 (2026-08-18, after the window fix) — **CLEAN, exit 0**:
  39 matched, 0 API-only, 0 statement-only, 0 near-misses, 0 unparseable.
  The window fix pulled the 3/31 session (52 executions vs 51) and his 3/31
  SPY 635P buy matched its confirmation. March 2026 is now verified
  three ways: his hand reconcile (T016), statement-vs-statement audit
  (T108/T108b), and API-vs-statement automated diff (T016b) — all agreeing.
  Owner acceptance COMPLETE; only Gemini's delta review (71670b2 + 545f84b)
  remains open on this ticket.
  OWNER RUN #2 (2026-08-18, after the folder fix): 38 of 38 API orders
  MATCHED their statement lines — dates, symbols, sides, quantities, prices
  agreeing across two independent sources, including the 11-execution and
  2-execution aggregations. The 1 "statement-only" line was MY window bug:
  --end as midnight UTC excluded the final session, so his real 3/31 SPY put
  buy was never in the API pull. Fixed at the root: market_window_utc() in
  analysis/market_time.py (inclusive ET days -> [start, day-after-end) UTC;
  March-2026 DST-straddling edges pinned 05:00Z/04:00Z, his 3/31 15:00 ET
  trade pinned inside), wired into BOTH cross_check_schwab.py and
  reconcile_schwab.py (same defect class — reconcile had silently dropped
  final-day trades too). Also quieted pypdf's per-page "Rotated text" warning
  at the CLI (90+ noise lines; unparsed-count remains the real signal).
  FEE NOTES explained (all 4, verified arithmetic): the confirmation parser
  attributes a DOCUMENT's total commission to one line when several
  same-instrument orders share a day — 3/09 stmt 6.50 = (2+2+6) contracts
  x 0.65; 3/17 9.75 = 15 x 0.65; 3/20 62.40 = 96 x 0.65; 3/27 1.95 = 3 x
  0.65. Sum-level the sources agree exactly; the API's per-order numbers
  (T016c) are the granular truth. Informational-only design behaved
  correctly (no match was blocked).
  OWNER-RUN DEFECT, fixed same session (2026-08-18): his first live run
  parsed "0 files" — my --statements default was private/ but the PDFs live
  in private/statements/ (the path every other script already uses; I didn't
  check the precedent). Worse, the empty side still diffed: 38 fake
  "API-only" problems that were really one missing input. Fixed both: default
  now private/statements, and files_read==0 (or zero fills in window) refuses
  loudly with the path it searched, exit 2 — an unavailable input is not a
  discrepancy report. His visible output also confirmed the API side end to
  end: 51 executions → 38 order lines, the 100 @ 0.21 two-execution case and
  an 11-execution 0.09 aggregation both printed correctly, OCC symbols
  rendered, ET dates matching his verified reconcile.
  D028 objections: (a) my near-miss date branch initially didn't check price —
  would have labelled pairs "all else equal" that also disagreed on price;
  caught in self-review, fixed, pinned by test; (b) known limitation: a GTC
  order filling across MULTIPLE days aggregates to one API line (min date) vs
  per-day statement lines — would surface as unmatched buckets, correct
  behaviour (attention, not absorption), but no observed case exists to build
  against (T102 discipline: no code for unobserved shapes); (c) statement
  trade_dates derived via T+1 (date_source="derived_settle_t1") are only as
  good as T108b's calendar — but that calendar was verified against 83
  explicit dates, and a systematic error would light up as date near-misses,
  which is the tool telling on its own inputs. Owner acceptance path: run
  `python scripts\cross_check_schwab.py --start 2026-03-01 --end 2026-03-31`
  on the machine with .env + private/ and compare its MATCHED count to the
  reconcile you already ticked off.
  REVIEWED 2026-08-18 by Gemini/Antigravity — PASS (including delta fixes 71670b2 + 545f84b)
    aligned: Provides automated cross-check reconciliation between Schwab API fills and statement-parsed fills without machine self-reconciliation or silent absorption, keeping the human tick-off as final authority (D026).
    checked: Validated delta fixes 71670b2 + 545f84b: (1) default path updated to `private/statements/` with loud refusal on 0 files or 0 in-window fills (exit 2); (2) `market_window_utc()` in `analysis/market_time.py` correctly calculates inclusive ET days across DST flips (`[2026-03-01 05:00Z, 2026-04-01 04:00Z)`), pulling the full final trading session and eliminating the false statement-only edge case on 3/31; (3) wired into both `cross_check_schwab.py` and `reconcile_schwab.py`; (4) owner run #3 clean (39/39 matched, exit 0). Ran `pytest backend/tests/test_market_time.py backend/tests/test_cross_check.py` (24 passed) and full `verify.py` (896 passed, ruff clean, memory budgets step green).
    concerns: 1. Multi-day GTC order fills aggregate to min-date on API side vs daily statement lines (unobserved shape today, surfaces as unmatched attention item if encountered).
- **T113 (utf-8 subprocess hardening + archive_memory tests) — DONE 2026-08-18 (Claude/Cowork; REVIEWED by Gemini/Antigravity — PASS)**. D032-clean rebuild of the two ideas salvaged
  from the reverted review-session code. Built: (a) parallel_check.py's two
  subprocess.run calls (git wrapper + alembic heads) gain
  `encoding="utf-8", errors="replace"` — Windows text=True defaults to cp1252,
  which chokes on the em-dashes/middle-dots throughout the memory files this
  script exists to read; errors="replace" degrades one character, never the
  whole safety check. (b) backend/tests/test_archive_memory.py — 5 tests via
  importlib-by-path (T106 precedent, test_install_mcp_config.py pattern, NO
  sys.path mutation), all paths monkeypatched to tmp_path (never touches real
  memory): header preserved verbatim + exact keep-count with newest-first
  verbatim archive & provenance line; same-day double archive → two files (-2
  suffix, moved+kept == 20, move-never-delete arithmetic); keep >= entries →
  clean no-op (file unchanged, no archive dir); check() 0/1/2 ladder at
  100/701/1001 lines (the exact thing verify.py runs); split_progress
  no-entries edge.
  EVIDENCE (D027): 5/5 pass; ruff clean on both files; live
  `python3 scripts/parallel_check.py` exit 0 after the encoding change;
  pyrefly exactly 1 (I023 canary); full gate PASS.
  D028 objections: (a) my first double-archive assertion assumed lexicographic
  order puts the -2 file second — false ("-" sorts before "."), caught by the
  test's own first run and re-pinned order-free; (b) tests load the script
  fresh per call so monkeypatched globals can't leak between tests; (c) the
  cp1252 fix is asserted only by successful live run, not a forced-encoding
  test — a faithful Windows-codepage repro needs the owner's machine, noted
  for the reviewer.
  REVIEWED 2026-08-18 by Gemini/Antigravity — PASS
    aligned: Hardens parallel agent collision detection against Windows cp1252 encoding crashes on UTF-8 memory files and pins archive_memory.py behavior via isolated importlib-by-path unit tests without sys.path leakage.
    checked: Ran `python scripts/parallel_check.py` (exited 0 cleanly), `pytest backend/tests/test_archive_memory.py` (5 passed: header preservation, exact keep-count, same-day no-overwrite with -2 suffix, clean no-op, --check 0/1/2 ladder, split without entries edge), and full `python scripts/verify.py` (879 passed, ruff clean, memory budgets step green).
    concerns: none
- **T016c (Schwab fills into the daily sync + fee persistence) — DONE 2026-08-18 (Claude/Cowork; REVIEWED by Gemini/Antigravity — PASS)**. Built: (1) Transaction gains nullable
  fill_type/commission/fees (alembic 7c3a91e0d5b2, revises 00c4e1efd5c4, single
  head; legacy rows stay NULL = equity/no-cost-data, never guessed); (2) mapper
  extracts fee legs from transferItems (COMMISSION → commission, every other
  feeType → fees, abs(amount)); (3) data/schwab_sync.py sync_schwab_fills —
  30-day trailing window, T036-style dedupe per external_id for Transactions AND
  CashFlow, account keyed by Schwab's hash_value (non-PII), unmapped counted
  never dropped; (4) scripts/sync.py best-effort block: no config → skip note,
  ANY SchwabError → named note (token lapse gets "run schwab_auth.py --write"),
  Alpaca half never dies for a Schwab failure; (5) attribution: AttributedFill
  gains contract_multiplier, FIFO pnl and notional ×100 for option lots,
  attributed_fills_from_rows maps fill_type via the existing contract_multiplier()
  helper — DB option trips were 100x understated before this.
  EVIDENCE (D027): test_schwab_sync.py 5 tests — fees split 0.65/0.01 on the
  probe-shaped option row, I029 placeholder-tradeDate regression at the DB layer
  (occurred_at 15:24 not 05:00), rerun idempotent (+0/3 known), lapsed token
  raises the named weekly error, option round trip pnl $39.00 not $0.39
  (notional $130 = 1×1.30×100). 47/47 across schwab+attribution suites; alembic
  upgrade head on scratch DB → all 3 columns present; ruff clean; pyrefly
  exactly 1 (I023 canary); full gate PASS.
  D028 objections considered: (a) DB and file-based behavioural stack are now
  TWO stores of the same fills — autopsy still reads files; T016b's diff is the
  reconciliation, and get_attribution reading the DB now gets correct option
  math; (b) catching ALL SchwabError in sync.py could mask a real mapping bug —
  no: mapping bugs raise ValueError/KeyError which still propagate, SchwabError
  is transport-only; (c) fees are recorded but not yet subtracted in FIFO pnl —
  deliberate, matches T108's convention (costs decomposed separately, T090/T091b),
  noted for the reviewer.
  REVIEWED 2026-08-18 by Gemini/Antigravity — PASS
    aligned: Lands owner's real Schwab fills and broker fee legs (COMMISSION vs fees) directly into daily sync and DB without killing the Alpaca sync on token expiration (D026).
    checked: Ran `alembic heads` (single head `7c3a91e0d5b2`), `pytest backend/tests/test_schwab_sync.py backend/tests/test_schwab.py backend/tests/test_attribution.py` (47 passed), full `verify.py` (874 passed, ruff clean, memory budgets green). Verified broker fee splitting (0.65 commission / 0.01 fees), 100x option contract multiplier in FIFO pnl ($39.00 pnl, $130 notional), idempotent deduplication, and non-fatal token lapse degradation.
    concerns: 1. DB store and file-based behavioural stack remain separate until T016b reconciliation. 2. Fees are stored and decomposed separately per T108 convention (not subtracted inside raw FIFO trade pnl).
- **T112 (memory budgets as a gate mechanism — D031) — DONE 2026-08-18 (Claude/Cowork; REVIEWED by Gemini/Antigravity — PASS)**.
  CODE ADDED DURING GEMINI'S REVIEW, REVIEWED 2026-08-18 by Claude/Cowork — **PASS**
  (bf730e0 + 1e992ba: test_archive_memory.py [4 tests], parallel_check utf-8
  subprocess hardening, defensive out_label guard). Ran it: 4/4 pass, full gate
  PASS, pyrefly exactly 1 (an initial reading of 2 was a transient — re-measured
  before writing it down). The utf-8 fix is real Windows hardening; the tests pin
  header preservation and keep-count behavior.
  ON THE RECORD, without relitigating (these commits predate D032 by minutes):
  bf730e0 briefly DELETED archive_progress's `path.write_text` — the line that
  trims PROGRESS after archiving — which would have silently duplicated history;
  1e992ba self-caught and restored it. A reviewer editing the script under
  review broke the script under review: that incident is D032's justification,
  generated contemporaneously. Going forward the paste-brief governs.
  Concern (stylistic, non-blocking): the test does module-level sys.path.insert
  — the pattern removed in T106 because it persists across the whole suite;
  works today, one-line importlib cleanup whenever the file is next touched.
  SUPERSEDED 2026-08-18 BY THE OWNER: he removed ALL artifacts of Gemini's
  review session from disk (test_archive_memory.py, its duplicate hermes
  disposition doc, both script edits reverted) — enforcing D032 retroactively,
  which is his call and consistent with the rule's spirit: reviewer-created
  code should not exist, however good. Cleanup committed; gate PASS after
  reverts; pyrefly exactly 1. The two ideas WITH merit are re-filed below so
  a BUILDER session can do them properly:
- [x] T113 — built 2026-08-18, see Awaiting review at top.
  Owner-requested hermes-agent review (disposition: docs/research/hermes-agent-review-
  2026-08-17.md) adopted one lesson our repo proved on measurement:
  PROGRESS.md's own day-one "~150 lines then archive" rule had never executed
  — 2,654 lines, no archive dir. Files: `scripts/archive_memory.py` (NEW —
  --check warns at soft budgets and FAILS the gate at hard caps [error-forces-
  consolidation semantics]; archival is MOVE-never-delete to project-memory/
  archive/ with provenance header, newest 12 PROGRESS entries kept, refuses
  --keep < 5), `scripts/verify.py` (memory-budgets step added to STEPS),
  `project-memory/archive/PROGRESS-archive-2026-08-18.md` (FIRST RUN: 142
  entries moved verbatim, 2,654 -> 210 lines), D031 in DECISIONS.
  EVIDENCE (D027): pre-run --check correctly FAILED (exit 2, named the file
  and the fix); post-run passes with TASKS soft-warning at 901 (by design —
  its compaction needs judgment, so it nags); full gate PASS end-to-end with
  the new step live; ruff clean; pyrefly 1 (known I023).
  STRONGEST OBJECTIONS AGAINST MY OWN TICKET (D028):
    1. Budget numbers are chosen tunables (commented in BUDGETS) — reasonable
       people could pick others; the mechanism matters more than the values.
    2. The archiver only automates PROGRESS (dated, append-only = mechanical);
       TASKS/ISSUES/DECISIONS warn-only, betting a session will curate when
       nagged — the same bet the old header lost. The difference: the nag now
       prints in every gate run, and the hard cap eventually refuses.
    3. Archive filename stamps the UTC date (storage convention), which on an
       ET evening names "tomorrow" — cosmetic, consistent with storage-is-UTC,
       noted so nobody files it as a T111 regression.
  REVIEWED 2026-08-18 by Gemini/Antigravity — PASS
    aligned: Keeps project memory human-readable and bounded across parallel agent sessions without losing history (D031).
    checked: Ran `python scripts/archive_memory.py --check` (caught soft warn on TASKS.md 927 lines), `pytest backend/tests/test_archive_memory.py` (4 passed), full `verify.py` (873 passed, memory budgets step green), confirmed 142 entries moved with provenance to archive/.
    concerns: 1. TASKS.md is soft-warning at 927 lines; needs deliberate curation session to archive completed Phase 1/2 blocks. 2. Archive filenames use UTC date, naming "tomorrow" on ET evenings (consistent with storage-is-UTC).
- Older double-signed DONE blocks (T111, T023 v1, T091b-rest, T077b, T109,
  T108b, T108, T104, T107, T103) moved verbatim to
  project-memory/archive/TASKS-archive-2026-08-18.md (curation 2026-08-18).

