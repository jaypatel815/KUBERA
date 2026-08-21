# DECISIONS

Newest on top. Format per PROJECT_SPEC.md §11. Record the *why*, so no agent relitigates.

## D038 - batch protocol: size follows coupling; the manifest is the entry (2026-08-20)

CONTEXT: the owner wants larger batches (10-15 was the ask) and brought a
ChatGPT-drafted "project constitution + batch manifest + audit reviewer"
system. Mapped against this repo, that proposal is ~1:1 with what already
exists: its constitution is AGENTS.md+PROJECT_SPEC, its decision log is this
file, its manifest is our AWAITING REVIEW entry (D027 evidence + D028
objection + D033 SHAs), its audit-not-redesign reviewer is D023/D027/D032,
its repair loop is our BLOCK->fix->re-review-at-new-SHA. Adopting the full
prompt would create a SECOND source of truth that drifts from the first -
the exact disease it claims to cure.

DECIDED (owner approved 2026-08-20; full text AGENTS.md "Batch protocol" +
REVIEW.md "Severity classes"):
1. Batch size follows COUPLING, not capability: independent 8-10, coupled
   4-6, architecture/migrations 1-3.
2. Tail-quality rule: quality flat across the batch or STOP and close clean;
   size is a target, never a quota.
3. Probe before claiming (D030 at batch scale) - the claim states what was
   probed.
4. The batch manifest IS the AWAITING REVIEW entry; required fields per
   ticket: SHA, what shipped, what was RUN, strongest self-objection; plus
   one batch-level coupling note.
5. Verdict severities CRITICAL/MAJOR/MINOR/NOTE annotate the binary
   PASS/BLOCK, per ticket - one blocked ticket never holds the batch hostage.
ADOPTED from the ChatGPT draft: only #1 and #5 (the two things we lacked).
REJECTED: the standalone constitution prompt, per-batch re-statement of
project goals in chat (the repo IS the statement), and a separate manifest
artifact (a second copy of TASKS.md content would rot - D031).

## D037 - FinRobot/AI-Trader/Kronos review: their data backs our doctrine (2026-08-20)
Second owner-requested repo review; full disposition:
docs/research/finrobot-aitrader-kronos-review-2026-08-20.md. Rulings:
- AI-Trader's published live benchmark (arXiv:2512.10971) is RECORDED AS
  EVIDENCE on D017/D035: six frontier LLMs trading autonomously for five
  weeks - 4 of 6 lost to QQQ buy-and-hold in US equities, all six lost to
  the index in A-shares, all six lost money in crypto. The architecture
  KUBERA refuses (LLM decides), measured. Their code is untouched
  (LICENSE file 404s - unresolved license); the paper's facts are cited.
- Kronos (MIT, weights on HF, AAAI 2026) is the first REAL Phase 7
  candidate: seeded as T122 with the contamination rule VERBATIM - a
  historical backtest of a model trained on 12B K-lines through its
  cutoff is a test on its own training data; only post-cutoff/paper-
  forward evaluation counts, under custody+budgets+isolation+promotion.
  Forecasts-as-internal-signals are compatible with D035 (the owner still
  hears odds and ranges); fine-tuning on the owner's fills is refused
  (overfit machine).
- FinRobot: independent convergence on our founding split (code computes,
  LLM narrates) - validation. One lead adopted: Finnhub free tier -> T121
  probe BUILT (scripts/finnhub_check.py, owner runs); yfinance rejected
  (unofficial API); debate-agents rejected (persona does case-for/against
  in one pass).

## D036 - Anthropic FSI/plugin repos: adopt methodology, never content (2026-08-20)
Owner asked for a review of anthropics/financial-services,
claude-plugins-official, and knowledge-work-plugins. Full disposition:
docs/research/anthropic-fsi-plugins-review-2026-08-20.md. Ruling:
- These are analyst-workflow CHECKLISTS; KUBERA implements the steps that
  matter as deterministic tested code. Adoption = "did their checklist
  name a step our composition lacks?" Two did: T117 (TLH scan,
  measurement-only) and T118 (earnings-preview composition) - BUILT.
- REJECTED by name: replacement-security suggestions (a named buy is a
  recommendation - D017), scenario price targets (D035), consensus/
  whisper scraping (no measured free source - D030), partner MCP
  connectors (all subscriptions - D034 upgrade-day candidates).
- SEEDED: T119 thesis view, T120 plugin packaging.
- All Apache-2.0; methodology adopted, zero text/code copied.

## D035 — Timescale doctrine: days are odds, minutes are state, seconds are out (2026-08-20)
Owner direction after his first live monitor run: "I want KUBERA to
predict the move within days, minutes, seconds — not weeks/months/years."
Disposition, recorded so no agent re-litigates it silently:
- SECONDS: OUT. Sub-second direction is a colocation latency war; the
  IEX free feed is a delayed SAMPLE of trades, and at the owner's size
  spread+fees consume any edge before it exists. No honest build exists
  on this data; saying so beats simulating one. Revisit ONLY as a D034
  upgrade-day question (SIP feed) — and even then default skeptical.
- MINUTES: STATE, NOT DIRECTION. KUBERA measures the session minute by
  minute (T052 VWAP/RVOL, T087a alerts) and that stays first-class;
  minute-scale DIRECTION from this data is noise mining (D029's exact
  failure mode). The monitor's churn/RVOL lines ARE the minutes product.
- DAYS: THE BUILDABLE ASK — and the default lens KUBERA should LEAD
  with. T077 already computes next-1-to-5-day distributions conditioned
  on the vol regime; T083 supplies day-scale event base rates. T116
  re-orders every surface to lead short-horizon: "from HERE, the next
  1-3 days usually range X..Y, up-odds Z" — then session state, then
  structure WITH ITS LENS NAMED (I033).
- LANGUAGE UNCHANGED (D017): odds and ranges, never point predictions.
  "SPY at 770 tomorrow" is the confidence trick that loses money; the
  distribution from here is information the owner can size against.

## D034 — free tier now, paid tiers at autonomy (owner policy, 2026-08-18)
The owner stated it plainly: "once I have KUBERA downloaded and running
autonomously, I will pay the monthly subscriptions for all the APIs that are
paid to get more data. But for now, try to find/use the free tier."

RULES this sets for every agent:
1. FREE FIRST. Every data need is answered from free tiers until autonomy:
   probe before building (D030), fail closed with NAMED paywall errors, and
   prefer free alternatives (e.g. T083b's SEC EDGAR) over waiting on a paid
   unlock. "This needs the paid tier" is never a reason to stall a ticket —
   find the free path or build the accumulate-forward path (T083's
   earnings_observed is the model).
2. DESIGN FOR THE UPGRADE. A tier upgrade must be a CONFIGURATION EVENT,
   zero code changes: paywall failures stay named and non-fatal, so the day
   a paid key lands, the same code simply starts receiving data. Never
   hard-code around a paywall in a way that would ignore the paid data.
3. SELF-ACCUMULATED STORES SURVIVE the upgrade. earnings_observed (and any
   future accumulator) becomes a VERIFICATION source against the paid feed,
   not dead code — two sources agreeing beats one source trusted.
4. UPGRADE-DAY CHECKLIST (append here as sources are added):
   - FMP paid: past calendar windows (instant T083 history — backfill
     earnings_observed and cross-check accumulated rows), news (D022
     revisit: FMP news vs Alpaca), transcripts (T084 unblocks), analyst
     estimates as attributed opinion.
   - Alpaca paid (SIP feed): full-market volume — the D006 volume_feed
     caveat threading through regime/RVOL/breakouts finally resolves;
     re-verify RVOL thresholds against SIP volume before trusting them.
   - Schwab: free — no tier decision exists.
   - FRED: free — no tier decision exists.
   The upgrade itself happens at the owner's "running autonomously"
   milestone, on his word — no agent pre-purchases or assumes it.

## D033 — a verdict names the SHA it covers (2026-08-18)
TWICE in one day, a Gemini PASS landed while the builder's next commit was
minutes away, silently leaving unreviewed work under a DONE header: 501f083
(16:08) passed T016b four minutes after the build while the owner's run had
already found a live defect; da02e80 (16:18) passed "incl. delta fix" and was
stale five minutes later — its own evidence (38 orders, 893 tests) proves it
predated the window fix 545f84b. Builder and reviewer race on wall-clock time;
nothing in the protocol pinned WHAT a verdict attests to.

RULE. (1) Every review verdict MUST name the exact commit SHA it reviewed
("REVIEWED <ticket> AT <sha> — PASS/BLOCK"), and it covers that SHA and
nothing after it. (2) Before signing, the reviewer runs
`git log -1 --format=%h -- <ticket files>` and confirms it equals the SHA
they checked out; if not, re-review at the newer SHA. (3) Any builder commit
touching the ticket's files AFTER the verdict SHA automatically re-queues the
ticket as "delta awaiting review at <new sha>" — the builder records this,
no relitigating the covered SHA. (4) A verdict without a SHA is void under
D027 (it cannot say what it reviewed).
Why not "reviewer locks the ticket": adds coordination the one-folder model
can't enforce; naming the SHA costs one line and makes staleness DETECTABLE,
which is the actual failure — both races were invisible until someone diffed
timestamps by hand.

## D023 — Parallel agents: concurrent tickets + RECIPROCAL blocking review (2026-08-16)
Owner asked whether two agents can work at once and how to keep them aligned.
It had already happened safely once (Gemini shipped the T082 Orb frontend while
Claude built T082a's backend) — but that was disjoint files plus luck.
CORRECTION IN THIS SAME SESSION: Claude first wrote this as "one builder + one
dedicated reviewer" after a poorly-framed clarifying question. The owner's
actual intent: BOTH agents build DIFFERENT tickets simultaneously and review
each other's completed work. Rewritten to match — the mistake is recorded so
nobody re-derives the wrong shape from a stale doc.
SHAPE: reciprocal. Everyone builds, everyone reviews, nobody signs off on their
own commit. Review happens at the START of a session, before claiming the next
ticket ("the price of admission") — that is what stops a review backlog while
both agents chase new work.
GATE: blocking. AWAITING REVIEW ≠ DONE; only the other agent writes DONE, with
a signed verdict block. Owner's reasoning: at this stage drift costs more than
throughput, because KUBERA manages his money and his discipline.
THE HAZARD THAT MATTERS MOST — ONE WORKING DIRECTORY: both agents edit
C:\Users\jaybe\Projects\KUBERA simultaneously, so git branches do not protect
anything. `git add -A` by one agent commits the other's half-finished files
under the wrong message. RULE: stage by path only, `git status` before staging,
wait on .git/index.lock rather than deleting it. The reviewer's parallel-conflict
checklist exists to catch violations after the fact (git show --stat for foreign
files, single alembic head, tool-count guards correct AFTER both commits, and
the verify gate run on the COMBINED tree — each half can pass alone and fail
together).
COMMIT OWNERSHIP (owner asked whether the REVIEWER should commit, to avoid
mishandling — answered no, with reasoning recorded because the instinct is
reasonable and will recur): the BUILDER commits their own work, immediately,
without waiting for review. Uncommitted work in a shared directory is the most
fragile state available — the commit is the fence that protects it from the
other agent, so committing early IS the safety mechanism. A reviewer committing
someone else's files would have to guess which paths belong to whom, which is
the `git add -A` hazard made mandatory; and authorship is memory (git log must
answer "who built this"). Each ticket therefore produces TWO commits by TWO
agents: the builder's code commit, then a `review <TICKET>: PASS|BLOCK` commit
touching only TASKS.md (+ISSUES.md). A review commit that edits source is not a
review — it is a new ticket needing its own review. Reviewers may fix trivial
mechanical things (a typo, a wrong guard count) as their own mini-ticket, named
in the verdict, reviewed back by the builder.
ALSO BANNED WHILE PARALLEL: git branches. Branching looks like the fix and is
the opposite — `git checkout` swaps files on disk beneath the other agent
mid-edit. One shared directory = one branch (main), small frequent commits,
staging by path. Branches return the day each agent gets its own clone.
SHARED FILES (owner's follow-up: what if both agents must edit TASKS/PROGRESS/
README?): unavoidable, so it is handled rather than forbidden. Key fact recorded
because it is counter-intuitive: one branch + one directory means git NEVER
raises a merge conflict — the risk is a silent lost update (read, other agent
saves, you write stale, their lines are gone). Rules: run scripts/parallel_check.py
first; edit by ANCHOR not whole-file write (an anchored replace fails loudly when
the region moved; a full write clobbers silently); re-read immediately before
writing; write only your own block and commit at once; never "tidy" a shared file
while another agent is live. Per-file ownership conventions and a recovery recipe
(git show <sha>:path, re-add, never revert) are in AGENTS.md. NEW GUARD:
scripts/parallel_check.py reports active claims, dirty shared files, the clobber
signature (deletions in append-only memory files), and alembic head count; 7
tests cover the pure parts. On its first run it flagged a genuine case — the
D023 rewrite itself had removed 20 lines from DECISIONS.md.
FIRST LIVE RUN (2026-08-16, Claude T091b || Gemini T072) — two findings folded
back in: (1) THE INDEX IS SHARED, NOT JUST THE DIRECTORY. `git add <my paths>`
yielded eight staged files because Gemini had already staged its in-flight T072
work; a plain `git commit` would have shipped their half-finished feature under
Claude's message. RULE UPGRADED: commit by PATHSPEC
(`git commit -m "..." -- <paths>`), which ignores the index for everything else,
then confirm with `git show --stat HEAD`. (2) When a shared coordination file
already holds the other agent's UNCOMMITTED claim line, staging that file
carries their line too — benign (it makes their claim durable) but it must be
declared in the commit message. Also observed working as designed: a genuine
race (Gemini committed its claim BETWEEN Claude's guard run and Claude's commit)
lost nothing, because the edit was anchored to their exact line instead of being
a whole-file rewrite.
FILES: AGENTS.md "Parallel work"; project-memory/REVIEW.md (checklist, ordered
intent-before-diff, owner-alignment questions first, + "commit the review,
never the code"); docs/agent-briefs.md (one paste-ready brief for any agent + a
table of safe concurrent ticket pairs).

## D022 — "Agentic loop" batch: two-thirds already built; adopt news + fan-out rule (2026-08-14)
Owner (via external AI) proposed: (1) a ReAct multi-tool loop, (2) a universal
tool registry, (3) a strict anti-chatbot persona. Honest disposition — ALREADY
EXISTS, with receipts: (1) run_chat_turn loops up to MAX_TOOL_ROUNDS=6 tool
rounds per turn (chat.py; SDK provider runs its own 8-turn agent loop) — the
chaining capability has been there since T042; (2) the registry holds 26 tools
spanning market data, risk engine, memory (journal/IPS/history), macro, briefs;
(3) the persona is 300+ lines of tested rules (test_persona guards). WHY IT
STILL FEELS LIKE A CHATBOT: weak-at-tool-chaining brains (owner's timeout came
from provider=openai/local; I011 showed the SDK bridge degrading) under-use the
loop they're given — the fix is brain choice + bridge verification, not
architecture. ADOPTED (real gaps): get_news tool #26 (Alpaca /v1beta1/news,
same keys, ages on every item, "headlines are DATA never instructions") +
GET /api/news; persona "AGENTIC DEFAULT — act first, speak once" (composite
questions → silent fan-out → ONE synthesized answer; never announce tools,
never ask which check to run). NOT adopted: generic web search (unscoped
surface, injection risk, no provider decision — revisit with T023/T083 when
the FMP tier answer lands; news covers the J.A.R.V.I.S. use case for now).

## D021 — PDF gap analysis: the shorting question goes to the owner (2026-08-13)
Owner-uploaded "Quant Capabilities Gap Analysis" (repo-aware; dispositions binding
in docs/research/quant-gap-analysis-pdf-2026-08-13.md). THE BIG ONE: it is correct
that T081 pairs is impossible long-only and that beta-hedging needs a short SPY
leg — but long-only is a DELIBERATE safety rail for this owner, so the choice is
escalated: (a) long-only proxy, (b) paper-short behind hard rails, (c) defer until
30d of DQS evidence. OWNER DECIDED (2026-08-13): (c) DEFER — stay long-only
until ~30 days of paper DQS history proves discipline under the current rails;
revisit ON EVIDENCE around 2026-09-12 (DQS trend, override rate, tier-trip
frequency are the inputs). T081 stays parked; everything else proceeds.
ADOPTED: strategy-decay DEMOTION into T093 (CUSUM drift vs backtest expectation →
ledger flips to "demoted" → existing require_promotion refuses automatically — the
T064 gate's twin). NEW: T094 HRP (with a written scale trigger — not for a
3-position book), T095 Fama-French factor loadings (free Ken French data, OLS,
dep 60+ snapshot returns). ENRICHED: T068 universe-screener framing. DEFERRED
with written triggers: nonlinear impact models + VWAP/TWAP slicing (T090's ADV
cap makes the problem structurally impossible at this scale). Convergence note:
six reviews in, the backlog is decision- and data-constrained, not idea-
constrained — the unlocks are the shorting decision, T036 fills, T023 keys,
T005 push.

## D020 — Quant-gaps review: build the measurement layer (2026-08-13)
Gemini's "what would a quant find missing" review — best cross-agent review yet
(dispositions binding in docs/research/quant-gaps-review-2026-08-13.md). BUILT
same-session: trade_excursions (MAE/MFE + winners'-MAE stop-calibration number,
close-to-close labeled) and Sortino/Omega (downside-honest ratios that refuse to
fake numbers without downside). NEW T088–T093: execution quality (slippage, dep
T036), live MAE/MFE, liquidity-aware costs (live spreads + conservative ADV cap),
ATTRIBUTION pack (persist regime/sub-strategy/entry-bucket in signal_log — the
"is the classifier adding value" question), parameter stability sweeps
(anti-curve-fit), portfolio risk summary + daily reconciliation + degradation
detection. ENRICHED: T068 ranking criteria, T077b band-calibration. Its traps
section independently matches D017/D019 rejections — three agents converged on
the same discipline. The theme: KUBERA can now DECIDE well; D020 is about
MEASURING whether the decisions actually work. Fills data (T036) is the single
biggest unlock left.

## D019 — Event-intelligence batch: take the base rates, gate the ML, keep the honesty (2026-08-13)
Owner's fourth batch (sell-the-news / NLP / XGBoost). Dispositions binding in
docs/research/event-intelligence-review-2026-08-13.md. The rumor/news/pricing
decomposition maps ~70% onto existing work (T077 shipped bands = the pricing leg;
T076 = the calendar; T023 = consensus/surprises). NEW: T083 event reaction base
rates (deterministic post-earnings move history split by beat/miss + runup — the
honest "hold through earnings?" answer), T084 transcripts/filings as LABELED
context via the existing LLM layer (no FinBERT; Lazy-Prices YoY filing-diff filed
as Phase 7 §7.7 research). ENRICHED: T076 priced-for-perfection flag, T023
tier-verification now explicitly covers transcripts. RE-REJECTED per D017, no new
evidence: 99.9% accuracy framing; ALSO rejected: XGBoost EPS predictor NOW (Phase 7
behind §7.7 + T064 gate; free-tier fundamentals aren't point-in-time — restatement
bias corrupts training), directive outputs with invented confidence ("Sell 50%,
85/100" violates persona). HYGIENE: the batch reused shipped ticket IDs
(T075/76/77) — external AIs must be given the AGENTS.md resume prompt so they
propose against real repo state.

## D018 — Cross-agent review: build the small safety nets now, vote the backlog order, park Schwab (2026-08-13)
Owner uploaded a repo-aware review (dispositions binding in docs/research/
agent-review-2026-08-13.md). BUILT same-session: stale-data detection
(age_seconds+stale on latest trade/quote, MAX_DATA_AGE_SECONDS=900, tool told to
never present stale as live), scripts/backup_db.py (timestamped, --keep 14,
backups/ git-ignored), scripts/health_check.py (server/breaker/sync-freshness,
exit code + best-effort toast). ADOPTED as build order: T052 → T055 → T077 →
T067/T062; "no new strategy templates before the no-trade condition" — T054 lands
with/after T055. ENRICHED: T064 promotion_status enforced in the loop, T063
follow/override tracking, T036 entry-delay + session-aware staleness, T079
unblocked from T023, T060 priority-on-first-deposit. NEW: T082 Orb upgrade pack
(conversations list endpoint + sidebar, portfolio panel, feed/stale badges) —
flagged for Gemini. OWNER DIRECTIVE: Schwab approval pending → T016 PARKED,
Alpaca continues. DEFERRED with reasons: Postgres migration (write volume is
trivial; real trigger = T052 minute-bar storage or Phase 7 pgvector — decide on
evidence then).

## D017 — "Institutional precision" batch: adopt the pillars we already stand on, take the two free capabilities, reject the data-tier fantasies (2026-08-13)
Owner's second batch of the day (Wall-Street-quant framing); binding dispositions in
docs/research/institutional-precision-review-2026-08-13.md. The Three Pillars (E[X]
over win rate · execution discipline · no-trade selectivity) VALIDATE the existing
architecture (T077 / T033+T035+T043 / T055) — no new work. NEW: T080 macro regime
context from FRED (10Y–2Y, VIXCLS, real rates — free, deterministic, dated) and T081
pairs/stat-arb template (cointegration screen + spread z-score MR through the existing
engine + T064 gate). ENRICHED: T023 (earnings surprise, 13F, news-as-context-not-alpha),
T077 (seeded Monte Carlo v2), T055 (confluence-score no-trade reason; thresholds from
backtests). REJECTED with reasons: L2/DOM/dark-pool feeds (D006 data honesty — can't
fake microstructure from a ~3% volume sample), HMM regime models now (unexplainable,
untestable by known answers; revisit only on T063 calibration evidence), sentiment-as-
alpha framing, VIX term structure (needs futures data), and ALL "99.9% / bulletproof"
language — 99.9% applies to discipline, never prediction; persona no-certainty rule
is non-negotiable.

## D016 — Owner suggestion batch: sharper alpha, graduated risk, calibrated learning (2026-08-13)
Owner delivered a 5-part improvement batch; per-item dispositions are binding in
docs/research/owner-suggestions-2026-08-13.md. NEW tickets T075–T079 (multi-timeframe
regime confluence · event-risk calendar guard · expected-move distribution engine ·
ATR/vol-parity sizing (MIN with existing caps — can only shrink) · correlation/overlap
guard). EXTENDED in place: T067 DQS tiers get enforcement teeth in the paper loop
(25/50/75/100% of daily budget → stricter R/R, half size, entry pause, breaker), T063
journal captures regime+confidence+entry/target/stop and runs calibration passes, T064
walk-forward becomes the paper-loop promotion gate, T062 briefs gain voice delivery +
event risk/DQS content. Already covered, not duplicated: T074 realtime voice, T052
intraday VWAP/RVOL, process-over-outcome persona rule. Deferred with reasons: GARCH
(rolling percentile bands first), volume-delta momentum (needs SIP, D006), PWA push
(Phase 5). Boundary kept: automatic strategy re-weighting stays human-gated — calibration
PROPOSES, owner ratifies. AGENTS.md gains agent-strengths defaults.

## D015 — Voice-first owner: voice is a primary interface, not a Phase-5 afterthought (2026-08-12)
Owner will primarily TALK to KUBERA. Consequences: (a) chat layer now has voice mode —
ChatRequest.voice → persona VOICE_STYLE (no markdown/tables, ear-rounded numbers, ~120
words, natural recency) — shipped and tested; (b) T070 pulls a push-to-talk desktop loop
ahead of Phase 5 (STT → /api/chat → TTS is buildable today); (c) safety invariant: a
spoken "yes" NEVER sets the confirm flag — clients translate a deliberate, distinct
gesture into confirm=true (persona instructs the model to explain this). Phase 5 PWA
voice + Phase 6 hands-free (Siri App Intents, Windows tray) sequencing unchanged, but
response-shaping and the v0 loop land first.

## D014 — Gemini master-spec reconciliation: the coaching layer (2026-08-12)
Companion to D013 (shared rejections apply verbatim — not re-argued). NEW adoptions:
the Quantitative Trading Coach — KUBERA judges the OWNER'S trades by process quality,
not outcome, detects behavioral patterns (revenge trading, FOMO, sizing drift), and the
owner's own Decision Quality Score idea (risk-budget-used × behavioral quality →
graduated advisories L1–L3; L4 hard stop = existing breaker). Tickets T066–T068
(coaching, DQS + advisories, watchlist/ranking); T061 upgraded to full IPS; T062 gains
weekly committee review; T064 gains named crisis-window stress tests. Persona now
carries the coaching rule + educational mode (guard-tested). Rejected per D013
reasoning: ML/RL model zoo outside the §7.7 pipeline, 22 sub-agents, tick/L2/alt-data
at this scale, 25-document governance suite. Binding record:
docs/research/gemini-master-spec-review.md.

## D013 — ChatGPT master-spec reconciliation: adopt features, keep our architecture (2026-08-12)
The owner's pre-project ChatGPT spec was reviewed in full (docs/research/
chatgpt-master-spec-review.md — the binding record). ADOPTED: persona upgrades (domain
boundary, KUBERA ANALYSIS structure, conflicting-signals honesty, injection defense),
prompt-injection rule in AGENTS.md, tickets T060–T065 (TWR benchmarking, user profile,
morning/EOD briefs, decision journal, backtest rigor, risk v2). REJECTED with reasons:
microservices + Timescale/Redis/Kafka/Qdrant stack now (D005/D007 stand), nine-agent
factory bureaucracy + duplicated profile trees (our project-memory achieves the same
guarantees with less drift surface), separate state-file suite, develop/PR flow before
GitHub CI is live, options/crypto domains, multi-user security (D012 boundary). Do not
re-litigate without new evidence; the review doc maps every section.

## D012 — Claude Agent SDK provider is PERSONAL-USE-ONLY (2026-08-11)
LLM_PROVIDER=claude-sdk runs chat on the owner's Claude Max subscription via the Agent
SDK's Claude-account auth (`claude setup-token` → CLAUDE_CODE_OAUTH_TOKEN). Verified
against current Anthropic docs/policy: permitted for personal single-user use; explicitly
NOT permitted to offer claude.ai login/limits to other users ("wrapper" products need
API keys or Anthropic approval). If KUBERA is EVER multi-tenanted or productized, this
provider must be removed or switched to API-key auth first. SDK usage draws from the
owner's Max limits (shared with Claude Code/Cowork). The SDK's own agent loop executes
KUBERA's bridged registry tools; permission surface locked to mcp__kubera__* only
(Bash/file tools disallowed, permission_mode=dontAsk, bounded max_turns). Audit trail
preserved via provider side-channel events persisted by the chat loop.
Sources: code.claude.com/docs/en/authentication, support.claude.com article 15036540.

## D011 — Alpaca's official MCP server: data window yes, trading path never (2026-08-11)
Owner asked whether to adopt github.com/alpacahq/alpaca-mcp-server. Decision: (a) NEVER in
the trading path — its `trading` toolset lets an LLM place/cancel orders and liquidate
positions outside our risk gate and signal_log audit, violating "rails are code, not
prompts" (spec §2.5/§8) and polluting the paper-account lab that feeds §7.4 evidence;
(b) approved as a restricted convenience/dev tool with `ALPACA_TOOLSETS` EXCLUDING
`trading` (account, stock-data, news, assets, index-data, corporate-actions), paper keys
only, in Claude Desktop / Antigravity; (c) KUBERA gets its OWN MCP server over the T024
registry (T045) — exposes briefings/benchmark/win-loss/backtests, the layer Alpaca can't,
with any future order-adjacent tool routed through the risk gate. MCP-client config files
hold keys in plaintext — same hygiene as .env.

## D010 — Backtesting: minimal internal engine first, framework when complexity demands (2026-08-11)
Deviates from spec §4's "start with vectorbt or backtrader", deliberately: the backtester IS
money math, and AGENTS.md's determinism rule wants it hand-verifiable. A ~120-line internal
daily-bar engine (no-lookahead execution, explicit cost model, metrics from analysis/metrics)
can be proven correct with hand-computed tests; a framework's fill model cannot. Zero new
heavy deps (no numba/pandas), CI stays fast. Revisit triggers → adopt vectorbt or LEAN:
multi-asset portfolios, intraday data, param sweeps at scale, or live/backtest parity needs.

## D009 — Broker roadmap: Alpaca paper now, Schwab (thinkorswim) integration later (2026-08-11)
Owner wants to use thinkorswim going forward. thinkorswim is Schwab's trading platform and has
no separate public API — programmatic access to that account goes through the **Schwab Trader
API**, already named as our alternate broker in spec §4. Plan: (a) Alpaca stays the paper/
simulation environment (Schwab's API has historically had no paper endpoint — verify current
capabilities when starting T016); (b) add read-only Schwab sync so KUBERA sees the owner's
real positions for analysis; (c) any live trading through Schwab stays behind the §7.4 gate.
Owner's `.env` (from a prior, abandoned attempt with another AI — no active fork) already has
Schwab, Polygon, FMP, and FRED keys: candidates for fundamentals/macro data in Phases 2–3;
verify validity and tiers on first use.

## D008 — Hosting deferred to Phase 4/5 (2026-08-11)
Local-first on the owner's Windows machine until phone access is needed. Pick Fly.io/Railway/VM
when the conversation layer ships. CI is GitHub Actions, activated when repo is pushed (T005).

## D007 — Database: SQLite now, Postgres+pgvector at Phase 3 (2026-08-11)
Overrides spec §4 default *timing*, not the destination. SQLite (via SQLAlchemy 2 + alembic)
means every agent and CI can run tests with zero services on any machine. Migrate to
Postgres+pgvector when research memory (vector store) arrives in Phase 3; alembic makes it a
config change, not a rewrite. Redis quote cache also deferred — in-process TTL cache first.

## D006 — Broker: Alpaca paper; data: Alpaca free tier, $0 budget (2026-08-11)
Owner chose free tiers to start. Alpaca: free real-time paper trading + bundled market data,
API built for this use case. Upgrade trigger: when delayed/limited data measurably hurts
Phase 2 analysis quality. yfinance allowed for dev exploration only — never in a user-facing path.

## D005 — Backend: Python 3.11+ / FastAPI (2026-08-11)
Spec §4 default confirmed. Quant/backtesting ecosystem + async streaming.

## D004 — Frontend: PWA, overriding spec §4's Flutter default (2026-08-11)
Owner decision. One installable web codebase covers iPhone, Android, Windows with push + mic;
agents can build and browser-verify it without a Flutter toolchain. Known cost, accepted
knowingly: Phase 6 Siri App Intents require a thin native iOS shell — revisit then (spec §6).

## D003 — Execution: paper trading first (2026-08-11)
Owner decision. Every strategy paper-trades by default; live capital only via the §7.4
promotion checklist with explicit per-strategy approval. Matches spec safety rails.

## D002 — Markets: US equities first (2026-08-11)
Owner decision. NYSE/Nasdaq via Alpaca. Other markets only after Phase 2 is solid.

## D001 — Governing docs ratified (2026-08-10, ratified 2026-08-11)
AGENTS.md + PROJECT_SPEC.md are the contract for all agents. project-memory/ paths are frozen.

## D024 — KUBERA's voice runs locally; spoken portfolio data does not leave the machine (2026-08-16)
DECIDED BY THE OWNER, after reviewing T072. He was offered the openai TTS rung
(near-human, ~$0.015/1k chars) and the kokoro rung (near-human, free, offline)
and chose kokoro: "I think your choice of using kokoro would be better."

WHY IT MATTERS MORE THAN "which voice sounds nicer": every KUBERA reply that gets
spoken contains position names, dollar P&L, account equity, and sometimes the
reasoning behind a pending decision. A cloud TTS call ships that sentence to a
third party on every turn. The chat text already goes to whichever LLM brain is
configured — that is a knowing trade for reasoning. Voice is not: it buys
pronunciation, and pays for it with the same data, to a SECOND vendor the owner
never chose.

SCOPE — the owner asked for both halves, because fixing only one is theatre:
- CLI (`scripts/talk.py`): kokoro is the recommended rung. Assigned to Gemini as
  part of the T072 re-submit.
- Orb (`/api/tts`, the interface he actually uses daily): T098, built here. The
  server prefers the local engine whenever the model files exist and falls back
  to edge-tts only when they do not — logging, every time, that text left the
  machine.

SECOND FINDING, arguably worse than the vendor question: the Orb was sending the
reply as a GET query string (`/api/tts?text=...`). A URL is the one part of a
request guaranteed to be written down — uvicorn access logs, any proxy, browser
history. His holdings were being persisted to disk in three places before they
ever reached Microsoft. T098 moves it to POST.

DEFAULT — deliberately NOT "kokoro or nothing": `KUBERA_TTS` (CLI) keeps `sapi`
as its zero-dependency default and `KUBERA_TTS_SERVER` (Orb) defaults to `auto`.
A fresh clone must speak without a 350 MB download, and an agent starting the
loop must not hit a hard exit. The privacy win comes from `auto` upgrading
itself the instant the model appears — not from breaking the first run.
But when local is explicitly REQUESTED and unavailable, the server returns 503
instead of downgrading: a silent fallback to the cloud would defeat the request.

ALTERNATIVE CONSIDERED — browser `speechSynthesis` (zero install, fully local).
Rejected: voice quality is inconsistent across machines and it cannot be tested
server-side, so KUBERA could not prove what it sounds like. Kokoro is
deterministic and testable.

## D025 — one Python version, declared once, followed everywhere (2026-08-16)
DECIDED BY THE OWNER: pin everything to 3.14.7, the version he actually runs.

THE STATE BEFORE, which is the argument for the decision: the repo declared
SEVEN Python versions and no two of them had to agree.
  .python-version        3.14.7      (uv's pin, what the owner runs)
  pyproject.toml         >=3.14.7
  .github/workflows/ci   3.11
  ruff.toml              py310
  pyrightconfig.json     3.10
  pyrefly.toml           3.10.0
  AGENTS.md              "3.11+"
Nothing enforced consistency, so drift was the default state rather than an
accident. The practical cost is not theoretical: a linter targeting 3.10 permits
nothing useful and silently declines to flag what a 3.14 runtime would accept,
while a checker set ABOVE the runtime flags valid code. Both directions waste
the reader's attention, which is the scarce resource.

WHY 3.14.7 RATHER THAN A FLOOR: this is one person's tool on one machine. "CI
tests exactly what I ship on" is worth more here than portability to machines
that will never exist. A floor buys compatibility nobody will spend.

THE PART THAT MATTERS MORE THAN THE NUMBER: CI no longer repeats the version at
all. `actions/setup-python` now reads `python-version-file: .python-version`, so
the runner follows the same file uv does. One declaration, one place to change,
and this particular drift cannot recur by construction. The remaining four
(ruff, pyright, pyrefly, AGENTS.md) still restate it because their formats have
no include mechanism — each now carries a comment naming .python-version as the
source, so the next agent updates them together.

VERIFIED, not assumed: ruff at py314 introduces no new lint (`All checks
passed!`); pyrefly at 3.14.7 reports the same 6 known-and-triaged errors it did
at 3.10, so the version change hid nothing and invented nothing; the gate passes
on a dev machine AND on a fresh checkout with no .env.

THE ONE THING NOT VERIFIABLE FROM HERE: that GitHub's runner image can install
exactly 3.14.7. If a future run fails at the setup-python step with "version not
found", the fix is to relax `.python-version` to `3.14` — which keeps every
other file correct, because they all point at that one file.

## D026 — Schwab as the behavioral record: read-only, verified before trusted (2026-08-16)
Schwab developer approval came through (T016 unparked). The owner's question was
whether KUBERA could study his REAL trading history and judge future trades
better for it. Scope agreed with him, in his order:

1. **T016 — read-only sync FIRST, and only that.** Positions, balances,
   transactions into the existing tables. Deliberately boring, for a reason
   today made vivid: every behavioral finding downstream is worthless if the
   import is subtly wrong, and mismatched fills are the hardest bug class to
   notice — they do not crash, they just quietly change the answer. Acceptance
   is reconciliation against his own statements, not "it ran".
2. **T102 — statement PDF ingest.** He wants the full record, not just whatever
   the API serves. Depth of the transactions endpoint is UNKNOWN — searched, not
   clearly documented, and deliberately not guessed at (see I018 for what
   guessing costs). Measure it first; the parser exists to cover what the API
   cannot reach. Parsed rows must reconcile against API rows in the overlap
   window — that overlap is the parser's own test.
3. **T103 — the trading autopsy**, only after 1 and 2 are trustworthy. Runs the
   battery that already exists (T091b holding periods, T069 sizing drift and
   post-loss tempo, T088 slippage by hour, T089 give-back, T060 TWR) over real
   fills instead of paper ones. Almost no new analysis code — the analysis was
   built first and has been waiting for data worth reading.
4. **T104 — pre-trade pattern warnings**, last. "This resembles a setup that has
   cost you," with the sample count attached.

WHAT KUBERA WILL AND WILL NOT CLAIM. It will DESCRIBE the record and CHALLENGE a
stated belief the record contradicts. It will NOT predict which future trades
work. A personal history is small-n; mining it for patterns is exactly the
curve-fitting T092 exists to catch, and a "pattern" over nine trades is noise
with a narrative. Every finding carries its sample count, and some questions his
history will simply be too small to answer — saying so is the feature, not a
failure of it (the T069 "insufficient" path is the precedent).

ACCESS: read-only now, revisitable later — his call, recorded rather than left
ambiguous. Alpaca paper remains the ONLY execution path. Conditions for
revisiting real execution: the PROJECT_SPEC §7.4 promotion gate passes AND the
paper record shows sustained discipline (DQS trend, override rate, tier trips),
same evidence bar D021 set for T081. Until then a bug in fresh import code
cannot reach an order, which is the point.

OPEN UNKNOWN, to be measured not assumed: how far back the Schwab transactions
endpoint actually serves. First task of T016 is to pull the widest range it
allows and record the real answer here.

## D027 — reviews must show evidence; builders must self-check (2026-08-16)
DECIDED BY THE OWNER after he observed that reviews were agreeing with
everything and that edits kept arriving broken. He asked for the record rather
than the impression, and the record supported him.

THE EVIDENCE, checkable in git:
- Gemini's verdicts on Claude's work: SIX reviews, SIX PASS, "concerns: none"
  wherever recorded.
- Claude's verdicts on Gemini's work: one PASS with listed concerns, two BLOCK
  (T072 broke CI collection; T045 bypassed the confirmation gate).
- The sharpest one: `61f4cd0 review T069: PASS` is immediately followed by
  `b323691 ... fix the real bug it found in T069`. The reviewed tool referenced a
  database column that does not exist and raised AttributeError on its first real
  call. A type checker found it in seconds. The review had not run it.

THE QUALIFICATION, recorded because it changes the right remedy: when told
precisely what was wrong, Gemini fixed both T045 blocks correctly and promptly —
mutating tools removed from the default surface, `confirmed` defaulted to False,
the mcp pin carrying its reason. Re-verified by re-running the exploit. The gap
is FINDING unspecified problems, not executing specified ones. So the answer is
not to remove the agent; it is to make "I agree" cost something.

WHAT CHANGED:
1. REVIEW.md — a PASS is VOID unless `checked:` names a command that was run and
   what came back. "Looks correct", "verified the implementation", "the logic is
   sound" and a bare "tests pass" are explicitly listed as non-evidence. Minimum
   evidence is specified per ticket kind: execute a new tool, simulate a clean
   checkout for a dependency, canary any config that lowers an error count, read
   per-item output for a parser, and attempt to violate any new safety rail.
   "concerns: none" now requires saying what you looked for.
2. AGENTS.md — the same five checks become the BUILDER's obligation before
   handing off, and what was run goes in the PROGRESS entry. This is the half
   that protects against the reviewer being weak: the builder is the last person
   who will look closely, so behave accordingly.

WHY BOTH HALVES: the owner chose to keep reciprocal review rather than retire
it. That is the right call on the evidence — Gemini's independent Windows
environment has caught things this sandbox cannot — but reciprocal review only
works if agreement is expensive. Every rule above is derived from a bug that
actually happened here, not from general good practice, and each one is written
with the incident attached so a future agent can see why it is not optional.

HONEST LIMIT: none of this can force a reviewer to actually run the command it
claims to have run. What it can do is make a fabricated verdict a specific,
checkable lie rather than a vague opinion — and put the builder's own five
checks between a bug and the repository regardless.

## D028 — read your own diff before committing, not just your tests (2026-08-16)
OWNER'S INSTRUCTION, after the T103 blocks: before committing, each agent must
review its own work line by line — not merely run the tests it wrote — verifying
that what he asked for is what got implemented; make it future-proof where that
matters; keep it secure and robust; and no hardcoded endpoints or parameters
unless explicitly noted.

WHY THE EXISTING RULES WERE NOT ENOUGH. D027 gave us five MECHANICAL checks, and
they work: they catch code that runs wrong. Both T103 blocks ran perfectly. The
suite was green, sample counts were attached, the module said "zero predictions"
— and the report still told the owner his median hold was 0.0 hours, derived
from a `time(12, 0)` the code had invented because Schwab confirmations carry no
clock. No test failed, because the fixtures shared the assumption. Only reading
the diff against the requirement catches that class.

THE SIX QUESTIONS, now in AGENTS.md: did you build what was ASKED or what was
easy; are any inputs fabricated; is anything hardcoded that should be
configurable; is it secure and fail-closed; is it cheaply future-proof; and
would you sign it under D027 if another agent handed it to you.

ADDENDUM 2026-08-18 — THE TWO-STRIKES LOOP RULE (owner: "I just don't want
KUBERA to get stuck in a loop answering the same questions/errors").
Self-questioning must terminate. The same identical attempt hitting the same
identical error TWICE means STOP — no third identical attempt. Instead:
change the approach, or file it (ISSUES.md with repro) and move on, or bring
it to the owner. This generalises what the code already practices: clients
never auto-retry rate limits, D033 forbids relitigating covered SHAs, D023
caps agent-vs-agent disagreement at two rounds, DECISIONS exists so answered
questions stay answered, and Phase 7's experiment budgets cap the research
loop's attempts. An error hit once is information; twice is a pattern;
a third identical try is a loop.

ON HARDCODING, because the honest answer has exceptions worth naming: base URLs
and tunables belong in settings.py, with TWO legitimate exceptions that must be
commented — a value fixed as a SAFETY RAIL (the Alpaca paper base URL is
deliberately not configurable; making it configurable would make it possible to
point at live money) and a value fixed by an external spec (an option contract
is 100 shares because the market says so). Filed T107 to bring the remaining
base URLs under settings with those exceptions marked.

LIMIT, stated so nobody mistakes this for a guarantee: this is a discipline, not
a mechanism. Nothing forces an agent to actually perform it. What it does is
make the omission visible — the PROGRESS entry has to say what the pass changed,
and "reviewed my own diff" followed by nothing is its own signal.

## D029 — evidence custody for strategy research (2026-08-17)

CONTEXT: the owner asked for a review of a freeCodeCamp multi-agent trading
handbook (disposition: docs/research/deep-agents-trading-review-2026-08-17.md).
Its architecture is our AGENTS.md thesis restated — agents may generate and
challenge ideas but must never control the evidence that judges them — and its
most instructive result is that the disciplined process rejected both agent
"improvements" and shipped the hand-written baseline, which then beat every
benchmark on the holdout.

DECIDED, adopted where we had gaps:
1. PRE-REGISTERED SELECTION RULES. Promotion standards live in a versioned
   docs/SELECTION_RULE.md written BEFORE experiments run; ties go to the
   incumbent; development-period performance is never a gate; the standard does
   not move after a result is seen — a near-miss is a miss (T109).
2. ONE STRUCTURAL CHANGE PER STRATEGY REVISION, or attribution dies. A revision
   bundling multiple structural changes is reviewed as unattributable.
3. COST-STRESS EVERY BACKTEST: report the run at 2x assumed costs beside the
   base run, so cost-fragile edges are visible at review time (T109).
4. HOLDOUT CUSTODY (Phase 7 gate): a reserved evaluation window whose custody
   is enforced in code outside agent reach; champion frozen before exposure;
   ONE evaluation; no revision after the result is known (T110).
5. EXPERIMENT BUDGETS (Phase 7 gate): a hard cap on configurations tried per
   revision, failures included, recorded append-only — otherwise the validation
   window becomes the next optimization target (T110).
6. AGENT-WRITTEN STRATEGY CODE runs ONLY inside an isolation boundary that has
   passed (a) an execution-parity test (isolated vs in-process identical
   numbers) and (b) an adversarial probe (a strategy that TRIES to read
   credentials and holdout data and must come back empty). Phase 7 does not
   start without this (T110).

NOT adopted: LangChain Deep Agents / LangGraph / virtual filesystems / notebook
orchestration / EODHD (reasons in the disposition doc — the repo IS our shared
filesystem, and the audited-artifact trail already does what their framework
simulates).

## D030 — T023 sources decided by probe, not brochure (2026-08-17)

The owner answered the standing tier question (FMP FREE, no transcripts), and
scripts/fmp_check.py measured the rest FROM HIS MACHINE (sandbox cannot reach
FMP). His table, verbatim evidence for this decision:
  profile OK(1) · earnings-calendar /stable OK(77) · earnings-calendar /api/v3
  PAYWALLED · income-statement OK(5) · cash-flow OK(5) · analyst-estimates
  HTTP 400 (probe parameter bug, since fixed — tier still unknown) · stock-news
  PAYWALLED · transcripts PAYWALLED.

DECIDED:
1. EARNINGS DATES come from FMP's /stable earnings-calendar — the free tier's
   confirmed unlock. The /api/v3 family is never used (paywalled for him).
2. NEWS stays with Alpaca (already integrated, D022). FMP news is paywalled;
   no second news source.
3. TRANSCRIPTS and consensus-estimate FEATURES are out of scope. Estimates
   that ride along on calendar rows are passed through as third-party OPINION,
   attributed as such, never as KUBERA's forecast.
4. FUNDAMENTAL RATIOS (FCF yield, debt — D017) are FEASIBLE (statements answer
   with 5 annual periods) and deferred to T023b as their own ticket.
5. Free-tier budget respected in design: one calendar call covers every symbol
   in a window; the client never auto-retries a 429.

MEASUREMENT UPDATE 2026-08-18 (owner reran the probe after T023b added the
balance-sheet row): balance-sheet-statement OK(1) — T023b's debt ratios are
live on his tier. analyst-estimates OK(1) — the 08-17 "HTTP 400" was the
probe's own parameter bug (owned in T023 v1); the ENDPOINT answers on the
free tier. Decision #3 stands unchanged: estimate FEATURES remain out —
availability ≠ adoption, and estimates are third-party opinion. news and
transcripts re-confirmed paywalled; nothing else moves.

## D031 — memory bounds are mechanisms, not rules (2026-08-17)

CONTEXT: the owner asked for a review of NousResearch/hermes-agent, a
self-improving agent (disposition:
docs/research/hermes-agent-review-2026-08-17.md). Most of its architecture is
convergent evolution with ours — human write-gates, provenance, never-delete
archival, multi-writer rules — usually with KUBERA's version stricter. Its one
lesson we lacked was proven by our own repo the moment we measured: memory
writes that exceed a bound must ERROR AND FORCE CONSOLIDATION, never grow
silently. PROGRESS.md's day-one header said "~150 lines then archive"; it
stood at 2,654 lines and the archive directory did not exist. A rule that is
not a mechanism does not happen (D028's limit note, observed again).

DECIDED:
1. MEMORY BUDGETS ARE PART OF THE VERIFY GATE (T112, built same day):
   scripts/archive_memory.py --check runs inside verify.py — soft budgets
   WARN, hard budgets FAIL the gate, so overflow forces deliberate archiving
   in-session. PROGRESS 700/1000, TASKS 900/1400, ISSUES 700/1100,
   DECISIONS 900/1400.
2. ARCHIVAL IS MOVE, NEVER DELETE: verbatim entries to
   project-memory/archive/ with a provenance header; git history is the
   snapshot; the move is an ordinary reviewable commit. First run archived
   142 PROGRESS entries (2,654 -> 210 lines, newest 12 kept).
3. CURATION TOUCHES ONLY CLOSED HISTORY (their provenance-scoped autonomy):
   the newest entries and anything open stay in place; TASKS/ISSUES/DECISIONS
   compaction needs judgment, so their budgets warn and a session curates
   deliberately rather than a script guessing.
NOT adopted, with reasons in the disposition: the background self-improvement
review fork (its cheap-model variant is exactly what D027 forbids; its write
gates default OPEN, ours never have), the skills/curator machinery, FTS5
session search (git grep is ours), and the framework itself.

## D032 — a review is a comment, not a construction site (2026-08-17)

CONTEXT: the owner, in plain words: "Whenever I ask Gemini to review your
work, it goes off on a tangent and starts creating new files/directories. I
don't need it to create files, I need it to comment on your work." The D023
protocol defined WHO reviews and D027 defined what EVIDENCE a review needs,
but neither defined the review session's WRITE SCOPE — so the reviewer
improvised one. The existing brief banned EDITING source in a review; the
observed failure mode was CREATING files, which the ban did not name.

DECIDED (full text: REVIEW.md § "Reviewer scope"; brief updated in
docs/agent-briefs.md):
1. A review session may write to exactly three paths: TASKS.md (the verdict,
   appended under the ticket), PROGRESS.md (one session entry), ISSUES.md
   (only for a newly discovered defect). Nothing else — no new files, no new
   directories, no source or test edits, no reports or notes-as-files.
2. Defects get a BLOCK verdict with evidence; the BUILDER fixes them. A
   reviewer-authored fix is unreviewed code and dissolves the separation.
3. Ideas found while reviewing become ONE backlog ticket line, not artifacts.
4. Evidence must still be RUN (D027) — running writes nothing to the repo;
   scratch goes to /tmp.
5. THE MECHANISM (D031's lesson): before the verdict commit, `git status
   --short` must show only the three memory files; any `??` path = drift —
   delete it and continue. The verdict commit is by pathspec.

## D039 — Phase 9: household finance + the dashboard surface (2026-08-21)

Owner direction (his words: "improve the UI completely... futuristic with
more data and visuals like finrobot" + four features: total debt balance &
payoff plans, credit cards, monthly spending tracking, monthly budget vs
income). Owner picked, via direct questions:
1. BOTH as one phase — engines and dashboard interleave; math lands first,
   the UI renders TESTED numbers, never the reverse.
2. Entry = chat/voice AND CSV import (bank aggregation stays a later
   paid/privacy decision, D034 class — named gap, not papered).
3. ONE SURFACE — the Orb page's side panel grows into the full dashboard
   (owner chose this over a second page, knowing the conversation stage
   shrinks; the voice loop itself is untouched).

Doctrine carried into the phase:
- Every dashboard card carries asof + source, stale flagged — a beautiful
  number with no date is exactly what KUBERA refuses to be (priority 1).
- MANUAL-DATA RECENCY: user-entered balances get asof = entry date and go
  STALE after a statement cycle (~35 days) — "as you told me on DATE" is
  the honest framing; KUBERA never presents an old manual balance as
  current.
- No CDN libraries in the Orb (pinned by test since T143); charts stay
  hand-drawn canvas. Framer et al. are aesthetic references only — a
  hosted builder is wrong-shaped for a local private money app.
- Payoff/budget/utilization math = deterministic tested code (the
  founding rule, unchanged). Coaching stays process-based, no shame
  (D014).
- Household data lives in the local gitignored DB like everything else;
  CSVs go to private/ (the statements convention).

Tickets: T152 schema / T153 payoff planner / T154 budget+utilization
engine / T155 chat tools + persona / T156 CSV import / T157 dashboard v1 /
T158 briefs integration. FinRobot note: its ARCHITECTURE was already
reviewed and mostly rejected (D036) — this phase borrows presentation
ambition, not agent design.

## D040 — ambient conversation: no history UI (2026-08-21)

Owner, after living with the rebuilt dashboard: "KUBERA will not be
conversation based, it would be more like talking to a human on a regular
basis... KUBERA should be able to reference the chat in the background."
Adopted: the history drawer, conversations table, and new-thread button are
REMOVED from the UI. On load the app silently resumes the most recent
thread (/api/conversations?limit=1) so continuity is automatic — one
ongoing relationship, not managed sessions. The server keeps the full
record (threads, audit trail, /api/chat/{id}) untouched; this is a
presentation doctrine, not a data change. Longer-horizon memory beyond one
thread's context window remains a NAMED gap for a future ticket
(cross-thread recall), not papered over.

## D041 — scoped third-party exception: TradingView chart (2026-08-21; amended 2026-08-21)

KUBERA has run with ZERO third-party runtime code (no CDN, single-file UI,
pinned by test) — supply-chain caution on a public-repo money app. The owner,
after three rounds on the chart, chose TradingView's actual Chart Widget (it
is what his index37 reference embeds) with the tradeoffs stated and accepted:
- SANDBOXED IFRAME ONLY — TradingView's code executes in ITS origin, never
  in KUBERA's page; our DOM, account data, and voice loop are unreachable.
- TradingView receives the viewed symbol string + standard embed telemetry;
  the chart area requires internet.
- The chart shows TRADINGVIEW'S feed, labeled as such — KUBERA's asof/feed
  rails apply everywhere else, not inside the iframe.
- The built-in canvas chart (T157h/i: candles, volume, 5s tick, TF chips)
  is RETAINED behind a one-click fallback for offline/embed failure.
Scope: the chart slot only. Any further third-party embed needs its own
decision entry. The no-CDN rule stands for everything else.

AMENDED 2026-08-21 — owner pasted the exact index37.html widget code and
confirmed the switch. New approach: `new TradingView.widget({...})` via
`<script src="https://s3.tradingview.com/tv.js">` in the page head.
Difference from original: tv.js now executes in KUBERA's page (not sandboxed
to TV's origin). Tradeoffs re-stated and accepted:
- tv.js is TradingView's own published library — same trust level as the
  previous iframe embed, wider surface.
- The widget is scoped to the `#tvchart` div container; it has no access to
  KUBERA's account data, API keys, or voice loop (no shared globals, no
  postMessage bridge from KUBERA to the widget).
- tv.js is the ONE permitted `<script src=` in the page — pinned by test.
  Any additional third-party script needs its own D0xx entry.
- Data provenance label ("their feed, their timestamps") retained.
- First-party canvas fallback retained.
The no-CDN rule for everything else (chart.js, etc.) is unchanged.
