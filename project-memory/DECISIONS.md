# DECISIONS

Newest on top. Format per PROJECT_SPEC.md §11. Record the *why*, so no agent relitigates.

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
