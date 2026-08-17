# DECISIONS

Newest on top. Format per PROJECT_SPEC.md §11. Record the *why*, so no agent relitigates.

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
