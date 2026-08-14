# DECISIONS

Newest on top. Format per PROJECT_SPEC.md §11. Record the *why*, so no agent relitigates.

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
