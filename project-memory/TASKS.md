# TASKS

One ticket = one focused agent session. Claim by adding your name as owner.
IDs never get reused. Format per PROJECT_SPEC.md §11.

**Current state (hygiene #7, 2026-08-20 — the old D018 build-order here
referenced tickets shipped a week ago):** batches run under D038 (size
follows coupling). The active front is the KRONOS CAMPAIGN — pre-registered,
gate OPEN, window 2026-08-24..2026-10-02; owner sequence: shape check →
`kronos_run.py start` → daily `forecast` → `score --consume` once at end.
The D021 revisit (~2026-09-12) decides shorts/pairs/HRP on evidence —
`scripts/d021_evidence.py` assembles it; risk-event history records from
2026-08-20. Owner actions that unlock the most: T007 finale, pushing to
origin (local runs ahead — CI confirms green only on push), and triggering
Gemini on anything in Awaiting review.

## In progress
## Awaiting review (D023 — a DIFFERENT agent signs these off; see REVIEW.md)
- **T157j: TradingView chart (D041) + VIX + Buying Power - AWAITING
  REVIEW 2026-08-21 (Claude/Cowork; SHA e9f0960).** Owner's formal
  redesign brief reconciled honestly (most mandates already shipped in
  T157g-i; corrections on record: no svc-* microservices, no WebSocket
  layer exist - REST polling is the truth). Genuinely new, all built:
  (1) owner chose TradingView's ACTUAL widget over first-party
  crosshair work - adopted per D041 with tradeoffs stated and accepted:
  SANDBOXED IFRAME only (zero third-party JS in our page - pinned:
  "<script src=" absent entirely), symbol-only URL, provenance labeled
  ("their feed, their timestamps"), built-in canvas engine RETAINED
  behind a named fallback toggle for offline/embed failure; (2) VIX as
  the 4th ticker (FRED VIXCLS chain; NO %% line - VIXY is a futures
  roll, an empty change beats a faked one); (3) Buying Power beside
  Day P&L on the account card.
  EVIDENCE (D027): gate PASS 1,206; node 0; pins extended (tvchart/
  sandbox/provenance/fallback/VIX/port-bp + no-script-src). D028
  objections: (1) TradingView embed is a live third-party dependency -
  scoped to the chart slot by D041, everything else first-party; (2)
  the widget's data may disagree with our feed by pennies/timing -
  labeled, and KUBERA's own numbers never come from it; (3) VIX change
  line empty without Finnhub index quotes - honest by design.
  REVIEWED 2026-08-21 by Gemini/Antigravity AT ed06bf3 (SHAs: e9f0960, 2b17b7d, ed06bf3) — PASS
    aligned: T157j — Sandboxed TradingView advanced chart iframe with first-party canvas fallback toggle (D041), VIX index ticker, and Buying Power KPI.
    checked:
      - T157j (PASS): Verified sandboxed iframe attributes, symbol-only URL, data provenance label, first-party fallback toggle, VIX FRED data chain without misleading %, and Buying Power placement.
      - RAN full gate: 1,206 passed, 3 skipped, pyrefly 0 errors, python pins agree: 3.14.7, node --check syntax clean on embedded JS.
    concerns: none.
- **T157i: real index levels + live-ticking candles - AWAITING REVIEW
  2026-08-21 (Claude/Cowork; SHA ee6f011).** Owner's two findings:
  index cards showed ETF dollars; candles read as static. Fixes:
  /api/indices with a PER-INDEX named chain (Finnhub live ^DJI/^GSPC/
  ^IXIC via new FinnhubClient.quote(), c=0 raised as refusal -> FRED
  official close, dated -> named unavailable; ETF may supply the %%
  line only, labeled; implied points derive from the LEVEL); candle
  panel ticks the forming bar every 5s while the market is open +
  LIVE/CLOSED badge that explains after-hours stillness (the owner
  tested Friday night - stillness was TRUTH, now stated on-card).
  EVIDENCE (D027): gate PASS 1,206 (+4 indices tests incl. the
  never-ETF-dollars pin); node 0; visibility-gated 12 req/min.
  D028 objections: (1) whether Finnhub free serves index quotes is
  key-dependent - unverifiable from the sandbox; the chain degrades
  named either way, owner's first load reveals the rung; (2) 5s tick
  updates the FORMING bar only - completed bars never mutate.
  REVIEWED 2026-08-21 by Gemini/Antigravity AT fc2317a (SHAs: ee6f011, fc2317a) — PASS
    aligned: T157i — Real index levels endpoint (/api/indices) through Finnhub/FRED chain, never ETF dollars as index values, live-ticking forming candles (5s interval), and market open/closed status badge.
    checked:
      - T157i (PASS): Read `backend/api/indices.py` and `backend/tests/test_indices.py`. Verified Finnhub/FRED fallback chain and named refusals; verified client-side forming bar live tick and market-hours guard. 4 unit tests pass.
      - RAN full gate: 1,206 passed, pyrefly 0.
    concerns: none.
- **T157h: owner-feedback round (repairs + D040 + index37 row) -
  AWAITING REVIEW 2026-08-21 (Claude/Cowork; SHAs per D033: 77e15e3
  repairs+D040 / c7d74cb index37 row / 361b094 calendar+matrix+positions).**
  Owner tested T157g live and filed 8 findings + new reference
  (index37); plan approved before build. REPAIRS: dead hero buttons
  root-caused (listener was #main-scoped; now ONE document-level
  [data-ask] delegation), home navigation restored (logo + home chip),
  performance chart refreshes every poll while visible. D040: history
  UI retired - silent auto-resume of the latest thread ("like talking
  to a human"); server records untouched; cross-thread long-memory a
  NAMED future gap. INDEX37 ROW: Dow/S&P/NASDAQ live cards (DIA/SPY/
  QQQ, labeled ETF proxies - free feed has no futures), rotating news
  banner from OUR licensed feeds ("headlines are data, not advice"),
  portfolio chart in the Main-Stocks slot, hand-drawn CANDLESTICK
  panel of the top holding: bodies/wicks/volume/y-grid/amber last-price
  tag, broker-clock market-open dot, day+52wk range sliders, TFs 5m
  (new /api/market/{sym}/intraday-bars route) / 1D / 1Y / 5Y (weekly
  aggregation, stated on-card - the owner's deep-history ask). PLUS:
  real calendar popover with amber event dots from new /api/events
  (published FOMC table + recorded earnings; empty store stated),
  trading-days matrix from real daily equity changes, positions table.
  EVIDENCE (D027): gate PASS 1,202 (+4 route/pin tests); node --check
  0 at every step; dangling-id scans clean x3; voice/PWA pins green.
  D028 objections: (1) index cards are ETF proxies not futures -
  labeled on-card; (2) "real-time" equity remains snapshot-granular
  (per-minute REFRESH, not intraday sampling) - intraday equity
  snapshots are a future server-side ticket, stated; (3) 5Y weekly
  aggregation is client-side presentation resampling (first/max/min/
  last/sum), not money math - stated in code and card.
  REVIEWED 2026-08-21 by Gemini/Antigravity AT 4376e94 (SHAs: 77e15e3, c7d74cb, 361b094, 4376e94) — PASS
    aligned: T157h — Owner-feedback round: document-level [data-ask] event delegation, home navigation, D040 thread auto-resume, index cards, live news marquee, top holding candlestick chart with multiple timeframes, /api/events FOMC calendar popover, trading days matrix, and positions table.
    checked:
      - T157h (PASS): Tested `/api/events` and `/api/market/{sym}/intraday-bars` routes. Verified JS event delegation and PWA layout pins.
      - RAN full gate: 1,202 passed, node --check clean.
    concerns: none.
- **T157g: the APPROVED index36 rebuild - AWAITING REVIEW 2026-08-21
  (Claude/Cowork; SHAs per D033: 4100c6d fonts infra / 9f32007 rebuild /
  close SHA on this commit).** Owner ran the full spec process himself
  (analyze -> map -> approve): reference = crypto-admin index36, his
  screenshot the pixel authority; his three calls locked (vendored OFL
  fonts via owner-run fetch_fonts.py + /fonts allowlist route; chat as
  hero mic-orb + amber FAB drawer, fixed dock retired; secondary views
  behind header icon chips). Built: reference chrome/hero/rows with
  KUBERA organs - equity in the VISA card anatomy, excess/day/debt as
  income rows with a REAL range chip, breaker circle + loss-budget
  donut, amber sparkline + DQS review card, monitor as Activity manager
  (quick-ask input, count pills, filter, P&L bars, payoff plan in their
  Upgrade shape), allocation as nested amber circles, session card on
  the real ET clock, every ask auto-opens the drawer. Voice loop
  byte-identical; asof survives on every card; no CDN (fonts local).
  EVIDENCE (D027): gate PASS 1,198 (+1 fonts test); node --check 0;
  dangling-id scan 0; pin suite extended (hero/micwrap/fab/cmd/donut/
  alloc/plbars/sess/mon-search + greeting + morning-brief CTA +
  openDock). docs/design/index36-qa.md carries the Phase-5 checklist
  with the two owner-eye items and four NAMED deviations.
  D028 objections: (1) fonts render as system stack until the owner
  runs fetch_fonts.py once - stated everywhere; (2) drawer-closed
  replies would be invisible, so EVERY send() opens it - a behavior
  the reference cannot exhibit but honesty requires; (3) the hero
  greeting hard-codes "Chotu" - it is his app, but a rename lives in
  one string.
  REVIEWED 2026-08-21 by Gemini/Antigravity AT 53287d7 (SHAs: 4100c6d, 9f32007, 53287d7) — PASS
    aligned: T157g — Approved index36 rebuild: vendored OFL fonts infrastructure (/fonts allowlist route + fetch_fonts.py), hero mic-orb, FAB drawer chat, VISA-card equity card, loss-budget donut, activity manager monitor, allocation circles, session ET clock card.
    checked:
      - T157g (PASS): Verified `/fonts` route security and local font delivery. Verified voice loop integrity and PWA pins.
      - RAN full gate: 1,198 passed, node --check clean.
    concerns: none.
- **T157f: the index36 experience - AWAITING REVIEW 2026-08-21
  (Claude/Cowork; SHA 74c85af; owner posted a SCREENSHOT of the exact
  target and said "follow it exactly... functionality, the look, how it
  behaves, and then just use the data that KUBERA gets").** The image
  corrected T157e: index36 is BLACK+VIOLET, not the family's blue
  dark-skin. Built to the image with behaviors on real payloads: pill
  nav -> three real views; matte radius-20 cards; violet-gradient HERO
  equity card; delta badges; live status pills (/api/risk,
  /api/monitor); inset sub-boxes whose corner arrows SEND questions to
  KUBERA; violet gradient-fill chart with hover tooltip + working
  1M/3M/6M range pills; conversations + debts tables. Asof lines
  survive on every card (doctrine). 3D illustrations + webfonts not
  reproduced (no assets/CDN, stated).
  EVIDENCE (D027): gate PASS 1,197 (+1 view test); node --check 0;
  pins all green incl. voice loop; benchmark fetch pin updated
  deliberately (template literal for range pills).
  D028 objections: (1) still browser-unseen by the agents - the
  owner's screenshot vs his render is the gate; (2) the Transactions
  view shows conversations+debts, not broker fills - a fills table
  needs an endpoint (T067c-adjacent) and was not smuggled in; (3)
  hero-card semantics: equity gains/losses render white-on-violet
  (their look) - the green/red lives in the badge.
  REVIEWED 2026-08-21 by Gemini/Antigravity AT fa2a350 (SHAs: 74c85af, fa2a350) — PASS
    aligned: T157f — index36 experience layout from screenshot: black+violet hero equity card, 3-view pill navigation, live status pills, inset prompt shortcuts, violet gradient chart with 1M/3M/6M range pills, asof timestamps preserved.
    checked:
      - T157f (PASS): Verified view switcher logic, chart range pills, and asof timestamp presence.
      - RAN full gate: 1,197 passed.
    concerns: none.
- **T157e: crypto-admin skin - AWAITING REVIEW 2026-08-21 (Claude/
  Cowork; SHA b76f444; owner: "more like the crypto-admin page").**
  THEIR STYLESHEET WAS FETCHABLE: bs5/main/css/skin_color.css adopted
  verbatim - field #0c1a32, glass tinted #112547, white-alpha
  hairlines, ramp #E9EEF9/#BDD1F8/#8CADE4/#566F9E, THE accent =
  their #ffa800 amber (their skin forces chart series to it; ours
  follows: "you" line, days lens, budget bar, wordmark). Link blue
  #4F80D5 = interaction; orb states amber/blues; gain/loss keep
  green/red (their skin defers semantics to Bootstrap); IBM Plex
  webfont NOT adopted (no CDN, D039). Doc tokens v3, v2 kept beneath.
  EVIDENCE (D027): stylesheet quoted in the doc; gate PASS 1,196;
  node --check 0; zero old-hex leftovers by automated scan; pins green.
  D028 objections: (1) still unseen in a browser - owner's eyes are
  the gate, third iteration of the designed loop; (2) two palettes
  now blended (crypto-admin base + buck-net semantics) - the doc says
  which owns what so a future pass doesn't muddle them.
  REVIEWED 2026-08-21 by Gemini/Antigravity AT 46194f3 (SHAs: b76f444, 46194f3) — PASS
    aligned: T157e — crypto-admin palette adoption: field #0c1a32, glass #112547, amber #ffa800 accents, link blue #4F80D5, doc tokens updated.
    checked:
      - T157e (PASS): Verified stylesheet color tokens and zero legacy hex leftovers.
      - RAN full gate: 1,196 passed.
    concerns: none.
- **T157d: the glass pass - AWAITING REVIEW 2026-08-21 (Claude/Cowork;
  SHA 2124b40; single-unit responsive batch #16 - owner sent round-two
  references and said "the glassy look" + confirmed the side-panel
  conversation).** THIS TIME THE PALETTE IS EVIDENCE: buck-net's own
  tailwind.config.js fetched raw and adopted literally (field #05050F,
  ramp #9292C1/#5A5A89, neons #007DF1/#00F1E7/#7517F8/#02C751/#FFB524/
  #F52C38); ha-component-kit = glass language; trading-vault = widget
  anatomy; crypto-admin + glasshome pages client-rendered (empty) -
  noted, not guessed. Glass cards (backdrop-blur 14px on translucent
  navy) over a glowing radial field; one hue per JOB (amber brand /
  teal data / blue interaction / purple thinking); orb states join the
  palette; manifest colors updated; doc tokens v2 with provenance.
  EVIDENCE (D027): gate PASS 1,196; node --check 0; automated scan for
  old-palette hex leftovers = zero; layout/voice/PWA pins untouched
  green. D028 objections: (1) backdrop-filter costs GPU on weak phones
  - if the owner's phone stutters, a reduced-blur media query earns a
  ticket from his report; (2) still visually unverified in a browser -
  same acceptance gate as T157c: the owner's eyes.
  REVIEWED 2026-08-21 by Gemini/Antigravity AT 4c98a65 (SHAs: 2124b40, 4c98a65) — PASS
    aligned: T157d — Glass pass: buck-net extracted palette, translucent navy cards with backdrop-filter, role-specific hue mapping, orb state styling.
    checked:
      - T157d (PASS): Verified CSS token mappings and layout pins.
      - RAN full gate: 1,196 passed.
    concerns: none.
- **Batch #15: T157a + T157b + T157c (dashboard v1) - AWAITING REVIEW
  2026-08-21 (Claude/Cowork; coupled UI batch, D038). SHAs per D033:
  df9c279 (T157a design language + T157b /api/household) / b9a3d56
  (T157c dashboard). ALSO in queue: batch #14 at a608682 and I039 at
  3ba7642 if not yet signed.**
  T157a at df9c279: docs/design/dashboard-language.md - tokens, card
  anatomy (label -> value -> chip -> ASOF, no exceptions), layout,
  doctrine rules. PROVENANCE STATED PLAINLY: the owner's six dribbble
  references are client-rendered (empty text-fetch) and his Chrome
  extension was not connected - nobody pixel-inspected them; the
  language is genre-derived and THE OWNER'S VISUAL REVIEW IS THE
  ACCEPTANCE GATE, recorded in the doc itself.
  T157b at df9c279: GET /api/household - debts + per-card utilization +
  D039 staleness flags + payoff compare from the tested T153 engine;
  impossible plans served as their named refusal; missing tables ->
  named 503. 6 tests incl. money-never-cached for the new route.
  T157c at b9a3d56: orb.html becomes the trading desk (owner's words:
  "neat, and not just an Orb"; his one-surface call): topbar, 6-KPI row
  (equity / day P&L / vs-SPY excess / risk tier + budget bar / DQS /
  total debt), card grid (performance canvas, monitor + bell, household
  payoff with "as you told me on DATE" stale rendering, positions),
  conversation docked right with the orb CSS-scaled - the voice loop is
  byte-identical and its pins stayed green untouched.
  EVIDENCE (D027): full gate PASS - 1,196 passed (+7: household_api 6,
  orb shell 1), pyrefly exactly 0, node --check exit 0 on the extracted
  JS, no-CDN pin green, leftover-element scan clean (portPanel/btn-port
  gone).
  D028 objections: (1) NOBODY has SEEN this layout render - CSS is
  structurally sound but untested visually; the acceptance gate is the
  owner opening it (stated in T157a; v1 -> his corrections is the
  designed loop, not a failure of it). (2) The dock is fixed 340px -
  no responsive collapse for phone-width yet; the PWA still works but
  the dashboard will crowd small screens; a media-query ticket earns
  its place from his phone report. (3) KPI risk fetch adds an
  /api/risk call per minute (alpaca account hit) - same cadence class
  as the existing portfolio poll; acceptable, named.
  REVIEWED 2026-08-21 by Gemini/Antigravity AT 89e4494 (SHAs: df9c279, b9a3d56, 89e4494) — PASS
    aligned: Batch #15 — Dashboard language spec (T157a), GET /api/household debts & payoff endpoint (T157b), dashboard v1 integration in orb.html (T157c).
    checked:
      - Batch #15 (PASS): Read `backend/api/household.py` and `backend/tests/test_household_api.py`. Verified `/api/household` payload integrity, staleness stamping, named refusals, and service worker never-cache rules. 6 unit tests pass. Verified dashboard DOM structure and voice loop untouched.
      - RAN full gate: 1,196 passed, pyrefly 0.
    concerns: none.
- **Batch #14: D039 + T152 + T153 - AWAITING REVIEW 2026-08-21
  (Claude/Cowork; Phase 9's coupled foundation, D038 4-6 rule). SHAs per
  D033: 534da08 (D039 + seeds) / 5a477fe (T152) / 1ac50b5 (T153) /
  close SHA on this commit. ALSO in queue: I039 voice fix at 3ba7642.**
  D039 at 534da08: owner-directed Phase 9 (household finance +
  dashboard; his picks recorded verbatim: one phase, chat+CSV entry,
  ONE SURFACE - the Orb panel grows into the dashboard). Doctrine
  carried in: manual-data recency ("as you told me on DATE", stale
  after a statement cycle), asof on every card, no CDN, payoff math =
  tested code, coach-not-scold. Seeds T152-T158.
  T152 - SCHEMA at 5a477fe: debts / recurring_flows / spending_entries
  + migration d4b8f1a6c2e5 (single head kept) + strict store: percent-
  shaped apr REFUSED with the conversion spelled out; due_day 29+
  refused naming February; every balance restatement restamps
  balance_asof; import_key UNIQUE (NULL-exempt) ready for T156
  idempotency. 9 tests.
  T153 - PAYOFF PLANNER at 1ac50b5: avalanche vs snowball, APR/12
  accrual, freed minimums roll (both strategies - fair comparison),
  same-month cascade. REFUSES plans whose payments cannot outrun
  interest, naming the debt and monthly shortfall; 100y horizon cap;
  debt-free is an answer. compare() states the interest delta AND that
  adherence is the owner's variable. 7 tests incl. an 11-month schedule
  worked by hand and the avalanche<=snowball invariant.
  EVIDENCE (D027): full gate PASS - 1,189 passed (+16: household 9,
  payoff 7), pyrefly exactly 0, alembic single head d4b8f1a6c2e5,
  budgets in bounds. The type gate REFUSED T153's first commit
  (heterogeneous-list indexing) - rewritten on a proper dataclass; its
  second live save.
  D028 objections: (1) APR/12 monthly accrual is the standard consumer
  approximation, not daily compounding - real card interest runs
  slightly higher; stated here and in the module docstring. (2) The
  payoff engine trusts owner-stated balances; balance_is_stale() is the
  defense and T155 must surface it in every answer. (3) cadence is
  monthly-only v1 - weekly paychecks need doubling by hand until a
  cadence ticket earns its place.
  REVIEWED 2026-08-21 by Gemini/Antigravity AT a608682 (SHAs: 534da08, 5a477fe, 1ac50b5, a608682) — PASS
    aligned: Batch #14 — Phase 9 foundation (D039), household schema & migration d4b8f1a6c2e5 (T152), debt payoff calculation engine (T153).
    checked:
      - Batch #14 (PASS): Read `backend/data/household.py`, `backend/analysis/payoff.py`, and test suites `test_household.py` and `test_payoff.py`. Verified apr_frac and due_day validation, balance_asof restamping, avalanche vs snowball schedule math, freed minimums rollover, and named refusals for insolvent payoff plans. 16 unit tests pass.
      - RAN full gate: 1,189 passed, pyrefly 0, alembic head `d4b8f1a6c2e5`.
    concerns: none.
- **I039 fix: voice-name validation + secret_check runtime-env parity -
  AWAITING REVIEW 2026-08-21 (Claude/Cowork; SHA 3ba7642).** Owner's
  /api/tts 500 (edge name into kokoro's assert). Fix + follow-through
  above in ISSUES.md I039. EVIDENCE (D027): incident reproduced as a
  test verbatim (edge name -> WAV with default voice, never 500); gate
  PASS 1,173 (+4); secret_check live run CLEAN with the new doc line.
  D028 objections: (1) fallback changes the VOICE the owner hears
  rather than erroring - deliberate: speech continuity beats cosmetic
  fidelity, and the log says what happened; (2) runtime-env parity
  scans backend/ only - scripts/ knobs stay checker-invisible;
  acceptable, .env.example currently documents no script-only vars.
  REVIEWED 2026-08-21 by Gemini/Antigravity AT 8399ba1 (SHAs: 3ba7642, 8399ba1) — PASS
    aligned: I039 fix — TTS voice name validation against model voices list, graceful fallback to default voice (af_heart), .env.example documentation, and runtime-env parity in secret_check.py.
    checked:
      - I039 (PASS): Tested `synthesize_local` and `POST /api/tts` with invalid/edge voice names. Verified 500 error eliminated; 30 unit tests across `test_tts_engine.py` and `test_secret_check.py` pass.
      - RAN full gate: 1,173 passed, pyrefly 0.
    concerns: none.
- **Batch #13: curation #13 + T150 + T151 - AWAITING REVIEW 2026-08-21
  (Claude/Cowork; probe-sized - T067c probed and left GATED with a dated
  note + the owner's check one-liner, D030). SHAs per D033: ed06ed2
  (curation #13 + T067c note) / 0c051a2 (T150) / 31a7c32 (T151) / close
  SHA on this commit.**
  T150 - RISK EVENTS IN THE WEEKLY at 0c051a2: T135 records tier changes
  and breaker trips as they happen; that history surfaced only in
  scripts/d021_evidence.py - evidence the owner would meet for the FIRST
  time at the Sept-12 revisit. Now the weekly review carries
  risk_events_week (counts, last event verbatim) and - deliberately - a
  quiet week as a STATED fact, because for the D021 decision an
  uneventful week is evidence too. Tests: quiet-week statement; counts +
  last-event quote.
  T151 - README DELTA at 31a7c32: campaign line (counts-only anti-peek
  stated), the bell (only-while-open stated), backup watch, weekly risk
  events. Each with its honest limit in the same sentence as the
  feature.
  EVIDENCE (D027): full gate PASS - 1,169 passed (+2 test_brief 18->20),
  pyrefly exactly 0, budgets in bounds.
  D028 objections: (1) risk_events_week uses a rolling 7x24h window
  (datetime.now - 7d), not market weeks - matches equity_history's
  7-day convention in the same review; stated here. (2) The quiet-week
  fact could go stale-confusing if recording ever breaks silently -
  accepted: the risk section OBSERVES on every brief run, so a broken
  recorder would also break briefs loudly.
  REVIEWED 2026-08-21 by Gemini/Antigravity AT 70f6f63 (SHAs: ed06ed2, 0c051a2, 31a7c32, 70f6f63) — PASS
    aligned: Batch #13 — Curation #13 (memory archiving & T067c probe note), weekly review risk events history (T150), README update (T151).
    checked:
      - Curation #13 (PASS): Verified archive file `TASKS-archive-2026-08-20.md` with Batch #12 double-signed record; T067c probe note verified (gate stands, query one-liner documented).
      - T150 (PASS): Read `backend/api/brief.py` and `backend/tests/test_brief.py`. Tested `compose_weekly_review` live in Python across quiet-week and populated risk event scenarios. Verified rolling 7-day window and quiet-week stated fact in `facts_for_lessons`. 2 unit tests pass.
      - T151 (PASS): Read `README.md` updates regarding campaign brief line, notification bell, backup watch, and weekly risk events (all with honest constraints stated).
      - RAN full verify gate: 1,169 passed, 3 skipped, pyrefly 0 errors, python pins agree: 3.14.7, alembic single head `c8e4f2a91d63`.
    concerns: none.
## Backlog — Phase 9: Household finance + dashboard (D039, owner-directed 2026-08-21)
- [ ] T152 — household schema: debts (kind incl. credit_card + credit_limit,
  balance, apr, min_payment, due_day, balance_asof), recurring_flows
  (income|expense, amount, cadence, category), spending_entries (date,
  amount, category, source manual|csv). Migration + store + tests.
- [ ] T153 — payoff planner: avalanche vs snowball, APR/12 accrual, extra
  payment, per-strategy payoff date + total interest, hand-computed tests;
  impossible plans (payment <= interest) refused by name.
- [ ] T154 — budget + utilization engine: month view of income vs planned
  recurring vs actual spending by category; leftover; per-card utilization
  (balance/limit) with the 30% caution line; pure + tested.
- [ ] T155 — chat tools + persona: add_debt / log_spending / add_recurring /
  get_household (composed view); manual-data recency rule ("as you told me
  on DATE", stale after ~35 days); coach-not-scold phrasing (D014); guard
  bumps.
- [ ] T156 — CSV spending import: card exports in private/ -> categorized
  spending_entries via owner-editable rule map; unknown -> "uncategorized",
  never guessed; idempotent re-import.
- [ ] T157 — dashboard v1 (owner chose ONE SURFACE): the Orb's panel area
  becomes the full dashboard grid — KPI cards (equity, day P&L, vs SPY,
  tier/budget, DQS), monitor, benchmark chart, household cards (total debt,
  payoff date under current plan, utilization, budget bar). Dark glass
  aesthetic; asof on EVERY card; esc() everywhere; no CDN (pinned).
- [ ] T158 — briefs integration: morning gains bills-due-7d + statement
  dates + budget pace; weekly gains spending-vs-budget summary.

## Backlog — Owner actions (Chotu — nothing else is blocked on these yet, but T005/T006 gate Phase 1 completion)
- [x] T099 — Give KUBERA its private voice — done 2026-08-16 (owner): installed `kokoro-onnx` and placed `kokoro-v1.0.onnx` + `voices-v1.0.bin` into `models/kokoro/`. Server and CLI speak locally with zero cloud leakage per D024.
- [x] T005 — GitHub repo created + remote added + main pushed (2026-08-16, owner). CI workflow active on GitHub Actions.
  NOTE: "pushed" and "CI green" are different things. CI is active and FAILING —
  the verify job exits 1 on runs #4 and #7. Tracked as I018.
- [x] T006 — Alpaca paper keys in `.env` — done 2026-08-11 (owner). Note: owner's `.env` uses `ALPACA_API_KEY` naming + extra vars from another template; settings loader accepts both spellings, extras ignored.
- [ ] T007 — **Phase 1 sign-off, nearly done:** verify.py passed on Windows 68/68 incl. the 3 live paper tests (per Gemini's 2026-08-11 session ✔). Remaining: `alembic -c backend\alembic.ini upgrade head` + `python scripts\sync.py` + open `http://127.0.0.1:8000/portfolio` once.
- [x] T008 — pre-commit installed — done 2026-08-11 (owner). Sandbox-side caveat: I003.

## Regime intelligence pack — ✅ COMPLETE 2026-08-13 (T050–T056 + T075 all shipped; doctrine: docs/research/regime-trading-notes.md)
- [ ] (future, logged) Options awareness: theta/IV warnings in low-vol regimes live in the doctrine; full options analytics is a separate future phase — do not build ad hoc.

## Backlog — Owner suggestion batch 2026-08-13 (docs/research/owner-suggestions-2026-08-13.md — read dispositions first; D016)
- [x] T076 — Event-risk guard (CPI/NFP half) — DONE 2026-08-14 (Claude/Cowork):
  `analysis/events.py` (pure calendar-day math: upcoming_events horizon list +
  entry_guard window reasons, fixed-date hand tests incl. window-0 semantics);
  `data/fred.py` release_dates via /fred/release/dates with
  include_release_dates_with_no_data (scheduled FUTURE dates; CPI=10,
  Employment Situation=50; actionable 400 errors); paper loop gains
  event_dates/event_window_days — a first-class T055 no-trade reason for BUYS
  only ("event window: CPI release … — new entries paused"); paper_trade.py
  arms the guard at startup when FRED_API_KEY exists (--event-window,
  --no-event-guard); get_macro_context surfaces upcoming_releases with a
  degrade-to-note on calendar failure.
- [x] T076b — built 2026-08-18, see Awaiting review at top (published-table
  FOMC dates + priced-for-perfection flag; earnings half was already done
  via T023/T083).
- [x] T077b — Expected-move v2 — DONE 2026-08-17 (REVIEWED PASS; record in
  archive/TASKS-archive-2026-08-18.md).
- [x] T079 — Correlation & overlap guard — DONE 2026-08-14 (Claude/Cowork):
  `analysis/correlation.py` (pearson/beta/log_returns pure + hand-tested: y=2x→1.0,
  hand-zero vector case, beta=2 doubling; overlap_report with aligned trailing
  windows, MIN_OVERLAP=20 refuse-don't-guess, HIGH_CORR=0.80 pair flags,
  candidate "adds exposure, not diversification" warning, portfolio beta from
  position weights w/ coverage warning). Tool `get_correlation` (#27, guard
  tests bumped in all three files) + `GET /api/correlation?candidate=&days=`.
  Persona-facing description orders the model to run it BEFORE recommending
  buys. T093's extension (marginal risk contribution, effective bets) SHIPPED with parts 1+3 — see analysis/portfolio_risk.py (T093c verified 2026-08-19).
- [x] T082a — Conversations index (the sidebar's BACKEND) — DONE 2026-08-14
  (Claude/Cowork): `data/conversations.py` list_conversations — ordered by LAST
  ACTIVITY not creation (a revived old thread belongs on top, proven in test),
  snippet taken from the owner's FIRST USER message with whitespace collapsed
  and 90-char ellipsis (never a system prompt or tool payload), turn count and
  tool-call count split so a thread shows how much evidence it pulled; empty
  conversations skipped. `GET /api/conversations?limit=` (1..200). 7 tests.
- [x] T082 — Orb upgrade pack FRONTEND — DONE 2026-08-16 (Gemini/Antigravity):
  `apps/web/orb.html` gains three additive panels with zero changes to the voice
  loop, canvas renderer, or send logic. (a) **Conversations sidebar** (left,
  `☰` toggle, collapsed-by-default): fetches `GET /api/conversations?limit=50`
  on load and after every `send()`; lists threads newest-activity-first with
  snippet + "N turns · M calls" meta; click any row calls `resumeConversation(id)`
  which sets `S.conversationId` and highlights the row; `+ new` clears the id.
  (b) **Portfolio snapshot panel** (right, `▣` toggle, collapsed-by-default):
  fetches `GET /portfolio` on open and polls every 60 s while visible; shows
  equity, day P&L colour-coded green/red, top-3 positions by market value;
  degrades to "broker offline" on 502/503. (c) **Freshness chip colours** (T082c /
  T036b): `get_latest`, `get_symbol_briefing`, `get_intraday` chips get a
  colour-coded border via a time-of-day heuristic (RTH 09:30–16:00 ET → teal
  live; outside → gold last_session). Layout uses a three-column flex shell;
  panel widths animate via CSS `transition: width`. No CDN dependencies added.
  HTML structural assertions: 25 IDs checked, all JS functions verified present.
  Verify: pytest gate requires owner's venv — run `.venv\Scripts\pytest -q`
  to confirm 615 passed, 3 skipped (frontend-only; existing tests unaffected).
- [ ] T081 — Pairs / stat-arb strategy template (D017): cointegration screen on log closes (Engle–Granger: OLS hedge ratio + ADF on residual spread, hand-computed tests on synthetic cointegrated series), spread z-score mean-reversion template on the T030 engine contract; runs the T064 walk-forward promotion gate like every template. ⛔ BLOCKED (D021, owner decided 2026-08-13): DEFERRED ~30 days — long-only stands until paper DQS history proves discipline; revisit on evidence ≈2026-09-12 (DQS trend, override rate, tier trips).
- [ ] T094 — HRP portfolio allocation (D021, gated): hierarchical risk parity (correlation-distance clustering + recursive bisection — deterministic, testable, no matrix inversion) sizing the whole book jointly. TRIGGER written down: build only when the book regularly holds enough positions that optimization beats common sense; T093's measurement half ships first.
- [ ] T095 — Factor loadings (D021): OLS regression of portfolio returns on Ken French factor series (free daily CSVs — market/size/value/momentum) → "is this alpha, leveraged beta, or an accidental size tilt"; dep: ~60+ daily snapshot returns. Beta-only version arrives earlier with T093.

## Backlog — Adopted from ChatGPT master-spec review (docs/research/chatgpt-master-spec-review.md)
- [x] T060 — Time-weighted returns — DONE 2026-08-14 (Claude/Cowork), built
  BEFORE the first deposit so the number is right the day it matters:
  `analysis/twr.py` — chain-linked sub-periods across external flows
  (convention documented: a flow dated D applies at the START of D), hand-
  tested on the headline case (1000→1100, +500 deposit, end 1760 → simple
  +76% is a lie, TWR +21% is the truth) plus the withdrawal mirror, flows
  outside the window, and a flow on the opening date (not double-counted).
  `cash_flows` table (migration 69a772af165c) + AlpacaClient.get_cash_activities
  (CSD/CSW, signs normalized) + data/flows.py sync (deduped like fills, wired
  into scripts/sync.py, never fatal). compare_benchmark now returns a
  time_weighted block with excess_vs_benchmark computed from TWR and a note
  telling the model to quote TWR, not the simple figure, once flows exist.
  Bug caught by the tz guard en route: date-only broker fields parse naive —
  normalized to UTC in the client.
- [~] T062b — Brief upgrades: watchlist setups (T068) + event risk (T076) DONE
  2026-08-14 (Claude/Cowork) — morning brief gains `watchlist` (top-3 ranked
  setups with the owner's thesis notes; empty list said plainly) and
  `event_risk` (upcoming CPI/NFP dates; no FRED key or calendar failure
  degrades to a note, core brief still delivers; fred is an OPTIONAL ToolContext
  member for get_brief, /api/brief constructs it best-effort). PENDING_NOTES
  trimmed to the earnings-dates gap (T023/T076b). REMAINING trimmed by hygiene #6
  (2026-08-20): ET-aware windows shipped as T036b/T111, scheduled
  generation as T062c (scripts/brief.py, no server needed) — both
  consumed. Still open here: PWA push delivery only (Phase 5, Flutter).
- [x] T063b — BUILT 2026-08-19, see Awaiting review (ships thin-data-honest now; grows informative as the journal ages).
- [x] T064b — Rigor follow-ups COMPLETE 2026-08-19: core (richer
  run_backtest + promotion expiry) DONE 2026-08-14; crisis-window stress
  runs BUILT 2026-08-19 (see T064b-rest in Awaiting review; 2008 named
  impossible on this feed). Promote-via-chat stays parked by design — the
  deliberate-act confirmation design doesn't exist yet; CLI remains the
  promotion instrument.
- [x] T065 — Risk engine v2 COMPLETE 2026-08-19 across two tickets: sector-exposure measurement + disable-symbol (T065, PASSED at 05dfe35-era review) and the order-frequency rail (T065b, see Awaiting review). Cancel-all deliberately unbuilt — nothing rests (market orders only); hard sector CAPS wait on owner-ratified limits (T061) by design.

## Backlog — Trading coach pack (Gemini spec, D014; doctrine: docs/research/gemini-master-spec-review.md)
- [x] T066 — built 2026-08-18, see Awaiting review at top. (Correlation
  section deliberately not duplicated — persona already orders
  get_correlation before buys; entry/exit PRICE quality needs exit prices
  on attribution trips, a future enrichment.)
- [x] T016c — built 2026-08-18, see Awaiting review at top. (Note: dedupe
  against the STATEMENT-parsed history by fill-signature was deferred to T016b
  — the DB and the file-based stack are separate stores today, and T016b's
  API-vs-parsed diff is the designed reconciliation between them.)
- [x] T067b — built 2026-08-18, see Awaiting review at top. (FOMO-into-late-
  RVOL deliberately NOT built — needs an intraday clock on every fill; named
  in every report and re-filed as T067c below.)
- [x] T121b - BUILT 2026-08-20, REVIEWED PASS by Gemini (batch #4; record
  in archive/TASKS-archive-2026-08-20.md). Stale seed closed by hygiene #6.
- [~] T122 - CAMPAIGN STARTED 2026-08-20: the owner ran `kronos_run.py
  start` on his machine - gate printed OPEN (all four rails, isolation
  0.10s), ATTEMPT 1 of 3 recorded, confirmed from the sandbox via
  `status` (1/3 used, 0 forecasts, window opens in 4 days). Remaining
  before Monday's first forecast: the SHAPE CHECK (kronos_shape_check.py
  with the model venv) - it costs no budget, and a broken adapter found
  Monday morning would cost a session's coverage instead (paper-forward:
  a missed session can never be forecast later). Then daily `forecast`,
  `score --consume` once after 2026-10-02.
  (was) PRE-REGISTERED 2026-08-20 (owner picked Kronos as the next
  front; Claude/Cowork executed the registration): docs/research/
  experiments/kronos-v1.md written BEFORE any run (symbols SPY/QQQ/NVDA,
  window 2026-08-24..2026-10-02 forward-only, calibration 80-97% coverage
  + toy-rule-vs-b&h success criteria pre-stated, FAIL is a real answer);
  holdout `kronos-v1-fwd` FROZEN on the live DB (params_hash
  f3237504f1c9e3b1); budget kronos-v1 opened at 3 attempts.
  `phase7_gate.py --revision kronos-v1` run LIVE: all four checks PASS,
  GATE OPEN (custody refused NVDA on the record). REMAINING: owner
  downloads the model (~400MB, huggingface); T122b (seed below) builds
  the runner. Original protocol text preserved below - it is now ALSO
  enforced by the gate script:
  (was) Kronos candidate experiment (Phase 7-GATED; D037; MIT model
  NeoQuasar/Kronos-base 102M params, CPU-feasible ~400MB F32). PRE-
  REGISTERED PROTOCOL REQUIRED BEFORE ANY RUN: (1) THE CONTAMINATION RULE:
  Kronos trained on 12B K-lines through its cutoff - a historical backtest
  is a test ON ITS OWN TRAINING DATA; only post-cutoff or paper-forward
  evaluation counts, full stop. (2) open_budget() BEFORE the first
  attempt; failures count (T110a). (3) holdout frozen before experiment
  one; consumed once (T110a). (4) any glue code runs inside the T110b
  boundary. (5) a Kronos-derived signal reaches the paper loop ONLY
  through the T064 promotion gate + selection rule, like every other
  strategy. (6) D035 stands: forecasts are internal signals; the owner
  hears odds and ranges, never "the model says 770". Fine-tuning on the
  owner's fills: REFUSED (D037).
- [x] T122b - BUILT 2026-08-20, see Awaiting review at top (runner +
  migration + JSON seam + gated CLI; 14 tests; live DB migrated).
- [x] T122c - BUILT 2026-08-20 (scripts/kronos_adapter.py, 121 lines,
  30-path distribution with sample_count=1 per draw - the model's own
  averaging parameter REFUSED; + kronos_shape_check.py; one-load
  forecast_batch via T140), REVIEWED PASS by Gemini after the I036 fix
  at 1a9ed3a (archive/TASKS-archive-2026-08-20.md, curations #9/#10).
  Stale seed closed hygiene #8.
- [x] T119 - BUILT 2026-08-20 (tool #44 get_thesis_view), REVIEWED PASS by
  Gemini (batch #4; archive/TASKS-archive-2026-08-20.md). Stale seed closed.
- [x] T120 - BUILT 2026-08-20 (.claude-plugin + commands/, owner installed
  live; manifest owner-object fix at fc2d7ff), REVIEWED PASS by Gemini
  (batch #4; archive/TASKS-archive-2026-08-20.md). Stale seed closed.
- [ ] T067c — FOMO-into-late-RVOL-spike detection (split out of T067b): flag
  entries made into a late-session volume spike. Needs BOTH an intraday
  timestamp per fill (the T016c Schwab sync now records execution times — let
  them accumulate) and that day's intraday volume profile (T052 provides it).
  Build only when real time-stamped fills exist to test against; approximating
  from date-only statement rows is exactly the guesswork T102 forbids.
  PROBED 2026-08-21 (batch #13): gate STANDS - the sandbox DB cannot see
  the owner's synced fills (his DB is local, gitignored); owner can check
  accumulation any time with: py -c "import sqlite3;c=sqlite3.connect(
  'kubera.sqlite3');print(c.execute('select count(*) from transactions
  where time(occurred_at)!=?',('00:00:00',)).fetchone())" - build when
  that count covers a few real trading days.
- [x] T068 — Watchlist + opportunity ranking — DONE 2026-08-14 (Claude/Cowork):
  `watchlist` table (migration 620eeac1a7c9) + data/watchlist.py (idempotent
  add updates note); `analysis/ranking.py` — cross-sectional scoring per D020:
  1/3/6-month (21/63/126-bar) relative-strength PERCENTILES within the list
  (tie-aware ranks, hand-tested), regime-fit mapping (trending_up 1.0 …
  trending_down 0.0, documented heuristic), 5-session payoff context, composite
  0.5/0.3/0.2, top/bottom decile flags (N≥10) else top/bottom; short history =
  listed-not-scored, never guessed. Tools #30/#31 update_watchlist (case-
  normalized add/remove) + get_watchlist (empty list → friendly offer, not an
  error; owner's thesis note rides along) + GET/POST/DELETE /api/watchlist.
  Cross-sectional momentum TEMPLATE (long top decile) remains future work
  behind the T064 gate; short half still awaits the D021 revisit.
- [ ] T074 — Realtime conversation pipeline (the Zoey-latency upgrade): streaming STT + start-TTS-before-reply-completes + barge-in. FRAMEWORK DECIDED by T074a research (2026-08-19, docs/research/realtime-voice-2026-08-19.md): **Pipecat** — LocalAudioTransport/SmallWebRTC need NO media server (LiveKit's room/media-server design is wrong-shaped for one user on one desktop), KokoroTTSService is a documented service so D024's voice drops in, fully-local stacks hit sub-second in the wild, $0/min. OpenAI Realtime REJECTED on architecture (a speech-to-speech model replaces the brain — persona/rails/tool gates bypassed), not just cost ($0.05–0.46/min measured). No Anthropic speech-to-speech API exists (re-check at build). Build via T074b→T074c below.
- [~] T074b — SANDBOX HALF DONE 2026-08-20 (api/voice_pipeline.py:
  KuberaChatProcessor routes TranscriptionFrame -> OUR /api/chat -> spoken
  TextFrame, conversation_id carried, failures spoken not swallowed;
  REVIEWED PASS after the I037 test-imports fix at e56c88b). REMAINING =
  owner-machine half: LocalAudioTransport + STT + kokoro wiring, latency
  + barge-in measurement (audio hardware cannot exist in the sandbox).
- [ ] T074c — (after T074b) VAD/interruption tuning, latency vs push-to-talk, Orb mode switch (SmallWebRTCTransport if browser audio beats PyAudio). Push-to-talk stays as a permanent fallback mode.
- [x] T072 — Human-grade TTS backends — DONE 2026-08-16 (Gemini/Antigravity; reviewed PASS by Claude/Cowork after one BLOCK round, fd1c10c + 483c522):
  `scripts/talk.py` `make_speaker()` now supports `KUBERA_TTS=openai` (OpenAI TTS API
  `tts-1` / `tts-1-hd` with voice choice via `KUBERA_VOICE`, default `alloy`, `OPENAI_API_KEY`
  required) and `KUBERA_TTS=kokoro` (local near-human via `kokoro-onnx` using `models/kokoro/`
  or `KUBERA_KOKORO_DIR`, default voice `af_heart`). Both fail fast with actionable install / download
  instructions if packages or model weights are missing; playback errors are caught and printed so
  the voice loop never crashes. Voice ladder documented in module docstring, `requirements-voice.txt`,
  and `README.md`. 8 tests in `backend/tests/test_tts_backends.py` (mocked, no hardware or network
  required; CI-safe via `pytest.importorskip` on BOTH numpy and soundfile — the numpy half was
  the BLOCK, see I016). Per D024 kokoro is the RECOMMENDED rung and every rung now states
  whether reply text leaves the machine. Carried forward as small follow-ups (T072b): the
  silent `except Exception` around the api.tts_engine import resolves `~` differently from the
  engine, module-level soundfile skip hides six audio-free tests from CI, and the docstring
  still says `pip install kokoro-onnx soundfile`.
- [x] T101 - pyrefly errors made expressible - DONE 2026-08-16 (REVIEWED PASS; record in archive/TASKS-archive-2026-08-20.md).
- [x] T100 - LLM_TIMEOUT_SECONDS in claude-sdk provider (I017) - DONE 2026-08-16 (REVIEWED PASS; record in archive/TASKS-archive-2026-08-20.md).
- [x] T045b — Owner: MCP acceptance run — DONE 2026-08-16 (owner):
  Ran `python scripts/install_mcp_config.py`; verified `%APPDATA%\Claude\claude_desktop_config.json` is configured with `.venv` Python interpreter and `scripts/mcp_server.py` stdio entrypoint.
- [x] T108 - expiry-aware FIFO closing - DONE 2026-08-17 (REVIEWED PASS; record in archive/TASKS-archive-2026-08-20.md).
- [x] T108b — Statement-transaction importer — DONE 2026-08-17 (Gemini/Antigravity,
  reviewed BLOCK→PASS by Claude/Cowork; full record in "Awaiting review" section above).
  Reconciliation 13/13 clean; the honest full-history record is now 131 fills, 80 trips,
  -$7,998.86 realized, 53.8% win rate (options -$11,706 / equities +$3,707).
- [x] T109 — Pre-registered selection rule + cost stress — DONE 2026-08-17
  (REVIEWED PASS; record in archive/TASKS-archive-2026-08-18.md).
- [x] T110 — Phase 7 preconditions COMPLETE 2026-08-19: T110a (holdout
  custody + experiment budgets, PASSED by Gemini at c54c7e9) + T110b
  (isolation boundary + adversarial probe — see Awaiting review). The
  D029 gate 'Phase 7 does not start without this ticket done' is now
  satisfiable: custody, budgets, parity-proven isolation, custody seam.
- [x] Owner (Chotu): June + July statements delivered 2026-08-17 — 735P x3 CONFIRMED
  exact (my "x12" was a stale pre-dedupe number; corrected), July verified as a
  no-trading month. Keep dropping each new monthly statement in as it posts.
  The missing-confirmation gaps (692P x8, 660P x8, 733P x35, NVDA 182.5P x2) wait
  for T108b — no need to hunt individual PDFs.
- [x] T107 — Base URLs into settings — DONE (Gemini built; Claude re-reviewed
  PASS 2026-08-17 at 516dca5). The two deliberate hardcodes stand with comments:
  Alpaca PAPER base URL (safety rail) and the option multiplier 100 (market
  fact). Full record in archive/TASKS-archive-2026-08-18.md.
- [x] T106 - MCP context lifecycle - DONE 2026-08-16 (REVIEWED PASS; record in archive/TASKS-archive-2026-08-20.md).
- [ ] T071 — Owner: voice acceptance run — `pip install -r requirements-voice.txt`, server up, `python scripts\talk.py`, hold a conversation. If faster-whisper wheels fail on Python 3.14 → `set KUBERA_STT=openai`. Report quirks to ISSUES.
- [x] T069 - adaptive risk-tolerance estimation - DONE 2026-08-16 (REVIEWED PASS; record in archive/TASKS-archive-2026-08-20.md).

## Backlog — Phase 2: Analysis & insight engine (agents)
- [x] T023 — Fundamentals + news ingestion — DONE via D030 (owner's probe
  decided sources) + T023 v1 2026-08-17 (REVIEWED PASS): FmpClient,
  get_earnings_calendar (#37), morning-brief earnings_risk. News stays Alpaca;
  transcripts/estimates OUT (paywalled). Full record in
  archive/TASKS-archive-2026-08-18.md. Follow-up split out:
- [x] T023b — built 2026-08-18, see Awaiting review at top.
- [x] T096 — Per-brain tool subsetting — DONE 2026-08-14 (Claude/Cowork):
  `api/tool_policy.py` — CORE_TOOLS (11: portfolio, briefing, latest, regime,
  exit plan, triage, size, brief, risk, record_decision, ips), is_small_brain
  (openai wire format + non-openai base_url = local runtime), tool_names_for /
  filter_schemas. Wired into run_chat_turn AND the persona's advertised list
  (the prompt now names exactly what's offered — a persona listing uncallable
  tools is how "capability missing" + phantom names are born, I008/I011) and
  into claude-sdk allowed_tools (bridge stays full; permission is the knob).
  `KUBERA_TOOL_PROFILE=auto|full|core` overrides either way; unknown values
  degrade to auto rather than killing a session. Guard test asserts CORE ⊆
  registry so a rename can't silently shrink a small brain. 11 tests.
- [x] T088 — Execution quality — DONE 2026-08-14 (Claude/Cowork):
  `signal_log.decision_price` (migration 00c4e1efd5c4) records the price each
  decision was made on; the loop fills it on every row. `analysis/execution.py`
  — slippage_bps with a SIDE-AWARE convention (positive ALWAYS = cost, both
  sides; hand-tested 4 ways), implementation shortfall in dollars, grouping by
  T091 entry bucket and side, MIN_BUCKET_SAMPLE=5 marking thin buckets as
  "anecdotes, not evidence". Tool #32 get_execution_quality joins
  signal_log.order_external_id ↔ transactions.order_id + GET
  /api/execution-quality; unmatched orders are counted and named (fills arrive
  after execution — run sync.py). Empty state is a calm answer, not an error.
  ⇒ "never buy the open print" becomes measurable from the owner's own fills
  once enough accumulate.
- [x] T089 — Live MAE/MFE — DONE 2026-08-16 (Claude/Cowork):
  `analysis/excursions_live.py` — per OPEN position: MAE (worst move against
  since entry, from daily LOWS), MFE (best, from HIGHS), current, GIVE-BACK
  (share of the run-up surrendered — the number behind "it was up 8% and I
  watched it round-trip"), and heat-used vs a 2xATR stop (capped at 1.0 =
  "another move against you triggers the exit"). Hand-tested headline case
  (entry 100, low 94, high 112, close 103 → −6% / +12% / 75% given back) plus
  corrupt-data and stop-above-entry rejection. Tool #33 get_open_excursions +
  GET /api/excursions; book-level worst_mae and biggest_give_back. Honest
  limits in EVERY payload: daily H/L (intraday spikes invisible) and the
  broker's AVERAGE entry as basis. Remaining from the original ticket: the
  winners'-MAE stop-calibration line in the T062 weekly review — needs closed
  trades to accumulate first (T063b/T091b territory).
- [x] T090 — Liquidity-aware costs — DONE 2026-08-14 (Claude/Cowork):
  `analysis/liquidity.py` (spread_bps, half-spread per-side cost with 0.5bps
  floor, ADV over trailing 20 sessions, 1%-participation cap — all hand-tested:
  99.90/100.10 → 20bps/10bps, 1M ADV → 10k-share cap). ADV cap now BINDS inside
  size_position (binding="adv_cap", IEX-understates note in every payload;
  shared BARS_JSON fixture given realistic uniform volume — RVOL-invariant).
  Tool `get_liquidity` (#28, guard bumps ×3; refuses one-sided quotes: "spread
  math would be fiction") + `GET /api/liquidity/{symbol}`. Remaining half
  parked in T091b/T062b: spread-aware cost line in briefings + paper-loop
  per-symbol cost_bps replacing the flat assumption (needs a quote fetch in
  the loop path — separate decision).
- [x] T091b — Attribution follow-ups. HOLDING-PERIOD HALF DONE 2026-08-16
  (Claude/Cowork): FIFO lots now carry their entry timestamp, so every round
  trip records held_days; `holding_period_distribution` reports count / win rate
  / realized P&L per bucket (intraday, 1-3d, 1-2wk, 2wk-1mo, over_1mo) plus
  median, mean, shortest, longest. Rides the existing `get_attribution` payload
  — no new tool, no guard-test collision. Undated lots land in "unknown" rather
  than being dropped; exit-before-entry and unparseable timestamps return None
  instead of a negative duration.
  REVIEWED 2026-08-16 by Gemini/Antigravity — PASS
    aligned: Tracks actual trade holding periods to detect style drift and early-cutting habits.
    checked: Half-open interval boundary edge cases [lo, hi), FIFO partial-sell multi-slice accounting, clock corruptions/undated lot handling in unknown bucket, get_attribution tool doc update, verify.py combined tree (663 passed).
    concerns: none
  REMAINING halves DONE 2026-08-17 as T091b-rest (REVIEWED PASS; record in
  archive/TASKS-archive-2026-08-18.md). Ticket fully closed.
- [x] T092 — Parameter stability sweeps — DONE 2026-08-14 (Claude/Cowork):
  `backtest/stability.py` — SWEEPS map (momentum lookback 20–90, sma_cross fast,
  mean_reversion window, range lookback), pure `stability_report` verdicts
  (insufficient / reject / curve_fit / stable; plateau = ≥50% of other points
  hold ≥50% of best Sharpe AND median > 0 — all hand-tested incl. the exact-
  boundary case), engine-only `run_sweep` (no ledger spam; never-invested
  params score 0 with warning). `stability_json` on backtest_runs (migration
  8d2d7f6c98b8) via `ledger.attach_stability` (lands on the template's latest
  run, loud failure otherwise). CLI `scripts/sweep.py momentum SPY [--record]`.
  Follow-up parked in T064b: surface stability verdict in run_backtest tool
  output + block promotion on curve_fit (needs owner sign-off on strictness).
- [x] T093 (parts 1+3) — Portfolio risk + CUSUM demotion — DONE 2026-08-14
  (Claude/Cowork): `analysis/portfolio_risk.py` (σ_p = √(w'Cw) hand-tested at
  ρ=1/0/−1, Euler contributions summing exactly to σ_p, effective bets 1/Σw²,
  diversification ratio, ≥60%-one-name warning) → tool #29 get_portfolio_risk
  + GET /api/portfolio-risk (thin-history holdings excluded with coverage
  warning). `backtest/decay.py`: expected_daily_return from the promoted run,
  one-sided CUSUM shortfall (hand-tested crossing day incl. an fp-boundary
  lesson), `demote()` flips passed→demoted so the loop's require_promotion
  refuses automatically (promote→demote→refused proven in test);
  `scripts/decay_check.py [--demote]` with the ACCOUNT-PROXY limitation
  printed every run.
- [x] T093b — Snapshot-vs-broker reconciliation — DONE 2026-08-14 (Claude/
  Cowork): health_check gains check_reconciliation — latest account_snapshot
  equity vs live /api/account, warns above 0.5% drift with the snapshot's age
  and the remedy named ("run sync.py; drift that SURVIVES a fresh sync is not
  normal"). Owns exactly ONE failure mode (both sides reachable, disagreeing);
  stays quiet when server-down/no-snapshot — those belong to the existing
  checks. Wired into run_checks → the owner's every-5-min scheduled task and
  --notify toast get it for free. 3 tests (drift/quiet/cannot-judge).
- [x] T116 — BUILT 2026-08-20 (batch #3, REVIEWED PASS): short_horizon.py +
  monitor/brief/persona all lead with the days lens (evidence: brief.py:87
  short_horizon in _symbol_read, persona.py:96 LEAD-with-range rule, tool
  #41). REMAINING split to T116b (event-aware lens — in batch #6). Original
  direction preserved below for T116b's contract:
  (was) Short-horizon FIRST (owner direction 2026-08-20, D035): every
  surface leads with the days lens — monitor/symbol briefing/morning brief
  open with "from HERE: next 1-3 day range p05..p95, up-odds, typical
  |move|" (T077 conditioned distribution + T083 base rates when an event
  is near), THEN session state (T052/T087a), THEN structure with its lens
  named (I033 pattern). Persona: when the owner asks "which way will it
  go", answer with the distribution + the honest sentence about why point
  predictions are refused (D017/D035) — never a bare label. Sweep ALL
  chat/brief surfaces for unlabeled-lens regime mentions (the I033 class).
- [~] T087 — Open-trade monitor: ANALYSIS + CLI shipped as T087a (2026-08-19), toast wiring as T087b, and the ENDPOINT as T087c (2026-08-20, api/monitor_service.py shared by CLI + GET /api/monitor — see Awaiting review). REMAINING here: the Orb panel (render /api/monitor's payload; the serialization is ready for it) and voice barge-in (dep T074) — delivery surfaces only, the judgment is done.
- [x] (advisory note, consumed) Fractional-Kelly VIEW — BUILT 2026-08-19 as
  T085b (REVIEWED PASS; kelly_view in size_position, capped, advisory-only).
- [x] T083 — built 2026-08-18, see Awaiting review at top. Post-probe
  redesign: past FMP windows are PAYWALLED on the owner's tier, so history
  self-accumulates in earnings_observed from the working forward window
  (three feed paths: base-rates tool, calendar tool, morning brief).
- [x] T083b — built 2026-08-18 (probe ALL GREEN same day), see Awaiting
  review at top. Years of earnings history now arrive instantly; real
  acceptance clocks replace bmo/amc guesses.
- [x] T084 — BUILT 2026-08-19, see Awaiting review (the gate was answered by the owner's probe the same morning; 10-K/10-Q YoY textual change stays a Phase 7 candidate).
- [x] T016a — Schwab read-only client + transaction mapping — DONE 2026-08-16 (Claude/Cowork, REVIEWED 2026-08-16 by Gemini — PASS):
  `backend/data/schwab.py` (OAuth token refresh, masked accounts, raw transaction queries, ImportReport with honest unmapped row logging), `backend/settings.py` (schwab_* settings and require_schwab), `.env.example`, `scripts/schwab_auth.py`, `scripts/reconcile_schwab.py`, `scripts/env_check.py`, and `backend/tests/test_schwab.py` (19 unit tests).
  REVIEW VERDICT: PASS. (a) `_equity_leg` safely isolates priced symbol legs from fee/currency legs; (b) `map_transactions` properly preserves execution prices and maps cash movements with signed amounts; (c) `_utc` cleanly parses standard ISO and legacy `+0000` formats; (d) read-only constraint verified via `dir(SchwabClient)` having zero order methods. Gate PASS (728 passed).
  LIVE ACCEPTANCE 2026-08-17 — REOPENED THE SAME DAY BY THE OWNER'S OWN
  TICK-OFF (I029), which is the reconciliation working exactly as designed:
  his March review caught (1) imported dates not matching when he actually
  traded (source-field problem — posting/settle time where execution time
  belongs; the settle-vs-trade class for the THIRD time: T102 statements,
  T108b importer, now the API) and (2) expirations presented as sales when
  his real proceeds were $0 (target state: expiry events at price 0 flagged
  closed_by="expiry_observed", feeding T108 as observation, never a sale).
  **T016 CLOSED 2026-08-17 (second close — the real one).** The full acceptance
  cycle, recorded because it is the model for every future data source:
  (1) owner reconciled March and CAUGHT discrepancies (I029) — my premature
  first "closed" retracted; (2) his probe delivered OBSERVED rows that
  corrected both of my hypotheses; (3) fixes landed against those rows only:
  mapper prefers `time` over the sometimes-placeholder `tradeDate` (regression
  test from observed row ...468374), reconcile prints EASTERN labeled, an
  EXPECTED EXPIRATIONS section lists never-sold lots at $0 (the API emits no
  row for them), and a BY ORDER section reproduces the statement's own
  settle-dated per-order granularity (his 71+29=100 @ 0.21 -> $2,033.48 tied
  to the penny); (4) owner RE-RAN and confirmed: "it does read like my
  statement." That confirmation, after fixes he forced, is the acceptance.
  The Schwab read-only sync is now trusted end-to-end. Unblocked: T016c
  (daily sync — persist the per-trade fees the probe revealed), T016b
  (automated diff under his final word), T066 (coaching on real fills).
- [x] T016b — built 2026-08-18, see Awaiting review at top.
- [x] T102 — Statement PDF ingest — DONE 2026-08-16 (Claude/Cowork, REVIEWED 2026-08-16 by Gemini/Antigravity — PASS):
  `backend/data/statements.py` parses Schwab confirmations (header trade date, settle date parsing with year boundary rollover, option leg extraction with contract multiplier, continuation window bounded by next row start); `backend/tests/test_statements.py` (12 tests); PII-redacted fixtures in `backend/tests/fixtures/schwab/` with regex identity audit test. Parses 250 fills from 86 real confirmations (147 options, 103 equity). Uncovered I020 (59% options, 62% 0DTE), unblocking T105 and pausing T103 until options land.
  REVIEW VERDICT: PASS. Verified all 4 review focus points: (a) positional row regex properly captures fields with tabular spacing and records unparsed failures without data loss; (b) `redact()` thoroughly sanitizes PII (accounts, addresses, long digits) and `test_committed_fixtures_contain_no_identity` guards fixtures; (c) header trade date extraction avoids 1-2 day settle date shift corruption; (d) agreed T103 must wait for T105 option modeling. Gate PASS (743 passed).
- [x] T105 — Options in the import and the analysis (I020) — DONE 2026-08-16 (Claude/Cowork, REVIEWED 2026-08-16 by Gemini/Antigravity — PASS):
  `backend/data/schwab.py` (`_security_leg` maps OPTION legs, uses `underlyingSymbol`, filters CURRENCY/FEE, assigns `fill_type="option"`), `backend/analysis/attribution.py` (`HOLD_BUCKETS` sub-day splits: minutes [<1h], hours [1-6.5h], same_day [6.5-24h]; `contract_multiplier` helper), and 5 unit tests in `test_schwab.py` + `test_holding_periods.py`. Unblocks T103.
  REVIEW VERDICT: PASS. (a) 1h / 6.5h session / same_day holding period cuts cleanly distinguish fast scalps from full-session holds without timezone math; (b) agreed that applying contract multiplier to `fifo_attribution` realized P&L belongs in a focused dedicated ticket; (c) filtering CURRENCY and FEE legs while extracting any security leg with symbol+price+amount is safe and complete across all Schwab asset types. Gate PASS (758 passed).
- [x] T103 — The trading autopsy (D026) — DONE 2026-08-16 (Gemini/Antigravity, REVIEWED 2026-08-16 by Claude/Cowork — PASS):
  `backend/analysis/autopsy.py` (TradingAutopsyReport: options vs equities, 0DTE share, FIFO round trips with 100x option contract multiplier and strike separation, sub-day holding period splits, honest unrecorded intraday duration handling for confirmations, T069 revenge sizing drift and tilt tempo detection strictly segregated within asset classes, per-symbol breakdown, honest deterministic narrative with N); `backend/api/tools.py` (`get_trading_autopsy` tool #35); `backend/api/main.py` (`GET /api/autopsy`); `backend/api/mcp_server.py` (`get_trading_autopsy` exposed in `_READ_ONLY_TOOLS`); `scripts/autopsy.py` CLI; `backend/tests/test_autopsy.py` (8 unit tests).
- [x] T104 — Pre-trade pattern warnings — DONE (Gemini built; Claude reviewed
  PASS 2026-08-16, key-drop fix re-verified 2026-08-17 at 516dca5; I026 caveat
  LIFTED by T108). Full record in archive/TASKS-archive-2026-08-18.md. This
  stale duplicate checkbox misled two sessions' "next" pointers — fixed by the
  2026-08-18 curation.
- [x] T036b — Session-aware staleness — DONE 2026-08-14 (Claude/Cowork):
  `analysis/staleness.py` — four states replacing the binary flag: live /
  stale (market OPEN but feed behind = the real hazard, untrustworthy) /
  last_session (market closed, most recent real print — TRUSTWORTHY, the
  Friday-quote-on-Saturday fix) / old (beyond a normal closure = check the
  feed), each with a narration-ready phrase; hand-tested incl. the 96h
  boundary and tz/future-timestamp validation. get_latest now consults the
  BROKER clock (ctx.alpaca optional — absent falls back to the conservative
  wall-clock rule labeled "market state unknown") and returns freshness +
  session (next open/close + "the market opens in 14h" hint). Raw stale flag
  and legacy payload preserved. /api/market/{symbol}/latest routes through
  the tool so the API and chat agree.

## Backlog — Phase 4: Conversation layer (agents; unblocked — §3 registry is done)
- [x] T047 — Owner activated claude-sdk: live /api/chat turn on the Max subscription verified 2026-08-12 02:22 UTC — KUBERA corrected the question's premise (holds SPY, not AAPL), full case-for/against, falsifiable risk level, persona disclaimers intact. Side-channel audit captured both tool calls. Quirk found+fixed: SDK usage is a dict (was parsed as object → 0/0).
- [x] T045 — KUBERA MCP server (D011) — DONE 2026-08-16 (Gemini/Antigravity, REVIEWED 2026-08-16 by Claude/Cowork — PASS):
  `backend/api/mcp_server.py` (FastMCP stdio server dynamically exposing all 30 read-only T024 registry tools by default with typed Pydantic signatures, docstrings, and configurable `ToolContext`; confirmation-gated `update_ips` unconditionally excluded; `confirmed=False` defense in depth), `scripts/mcp_server.py` (stdio CLI entrypoint for Claude Desktop / Antigravity), and `backend/tests/test_mcp_server.py` (9 tests). Gate PASS (760 passed).
- [x] T045b — Claude Desktop config installer (`scripts/install_mcp_config.py`) — DONE 2026-08-16 (Claude/Cowork built installer, verified by Gemini; owner executed installer and verified config at `%APPDATA%\Claude\claude_desktop_config.json`):
  Locates `%APPDATA%\Claude\claude_desktop_config.json`, resolves absolute path to venv interpreter, merges without clobbering other MCP servers, backs up existing file, guards against missing `mcp` import before write. Tested via `test_install_mcp_config_merge`.

## Blocked
(none)

## Done
- Full early-phase DONE list (T098 back to T001) moved verbatim to
  project-memory/archive/TASKS-archive-2026-08-18.md (curation 2026-08-18).
