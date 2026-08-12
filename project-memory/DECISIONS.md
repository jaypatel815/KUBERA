# DECISIONS

Newest on top. Format per PROJECT_SPEC.md §11. Record the *why*, so no agent relitigates.

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
