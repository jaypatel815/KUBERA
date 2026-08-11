# KUBERA — Project Specification

*Master reference for every AI agent working on this project. Read `/AGENTS.md` first — this document is the detail behind it. You don't need to read this whole file every session; jump to the section for your current phase or module.*

## 0. Document map
- §1 Vision & what "done" means
- §2 Non-negotiable principles
- §3 Architecture
- §4 Tech stack
- §5 Your multi-agent team
- §6 Voice & cross-platform: what's actually possible today
- §7 Phased roadmap
- §8 Safety rails specification
- §9 Testing & definition of done
- §10 Regulatory notes
- §11 project-memory/ file templates
- §12 Session kickoff template

## 1. Vision & what "done" means

KUBERA is a personal financial research and portfolio-management assistant for one user (the product owner reading this), covering their own brokerage account(s). It should feel like talking to a sharp, careful research analyst who never sleeps — not like talking to a chatbot that happens to mention stocks.

**In scope:** real-time portfolio tracking; research and analysis grounded in live data; short-term (technical/momentum) and long-term (fundamental) framing on the same question; benchmark comparison against the S&P 500 and other funds; a visual win/loss breakdown across positions; backtested strategy development; paper trading; and — once a strategy has earned it — semi-autonomous live trading within hard risk limits, all accessible via chat and voice on iOS, Android, and Windows.

**Explicitly out of scope for this build:** managing anyone else's money, the kind of advice that requires RIA/broker-dealer registration (§10), and fully unsupervised strategy changes reaching live capital without your sign-off.

**Three phrases from the original brief, translated into buildable requirements:**
- *"No static or hardcoded content"* — every number KUBERA shows you (a price, a position, a return, a headline) must come from a live source at the time you ask, never a mock fixture or a stale cache treated as current. The code that computes and displays those numbers is, like all software, written in code — that's not what "static" means here. What must never be static is the *data*.
- *"Continuously learning"* — KUBERA should never stop researching, backtesting, and proposing improvements. What it proposes should never silently start trading with your money — see the promotion gate in §7.4. A trading system that quietly rewrites its own logic in production is a liability, not a feature; that would actually undermine the "trustworthy, robust" bar you set, not serve it.
- *"Behave like JARVIS"* — a natural, persistent, voice-and-text conversational layer that knows your portfolio and can be invoked hands-free. §6 lays out exactly what's achievable on each platform today so this doesn't turn into a surprise late in the build.

## 2. Non-negotiable principles

Every agent, every session, regardless of which tool you are:

1. **Determinism for money.** All financial arithmetic (returns, CAGR, volatility, drawdown, position sizing, order quantities) is tested, deterministic code. The LLM explains and contextualizes; it does not calculate. See §3's tool-calling contract.
2. **The LLM's job is language and judgment, grounded in tool calls.** Every claim it makes about the user's portfolio or the market comes from a real, timestamped data fetch or a call into the deterministic layer — never from memory or plausible-sounding invention.
3. **No mock data in any user-facing or execution path.** Fixtures live only in test directories.
4. **Every output is explainable and dated.** Show data recency, cite what the recommendation is based on, state the key risk or assumption. Never present a recommendation as certain.
5. **Safety rails are code, not prompts.** Position caps and loss circuit breakers are enforced where the LLM cannot reason around them.
6. **Paper trading is the default.** Live capital is opt-in per strategy, per §7.4.
7. **Everything is logged.** Every recommendation, signal, and order — timestamped, with its inputs — so you can always answer "why did KUBERA do that."
8. **Least privilege.** Broker API keys scoped to trading only (no withdrawal) wherever the broker supports it; secrets never touch git; 2FA on every account in the chain.
9. **Personal use only.** This build is scoped to your own capital — see §10 before ever changing that.

## 3. Architecture

- **Clients** — one codebase targeting iOS, Android, Windows, and web (§4), talking to the backend over a REST/WebSocket API. Chat UI, portfolio dashboard, benchmark charts, push notifications, and (from Phase 5) in-app voice.
- **Backend API** — the conversation engine (LLM + tool-calling) sits behind it. It's the only thing clients talk to directly.
- **Deterministic engine** — analysis (metrics, benchmark comparison), backtesting/strategy sandbox, and the risk/execution gate. Pure code; no LLM in the loop for the numbers themselves.
- **Research agent** — a separate, lower-privilege process that reads news/market data/web research on a schedule and writes *proposals* into the backtest sandbox. No write access to the risk engine or the broker connection.
- **Data layer** — a relational database for users/accounts/positions/transactions, a vector store for KUBERA's own research memory (so it doesn't re-derive analysis it already did), and a cache for real-time quotes.
- **External integrations** — broker API (positions, orders), market data API (quotes, fundamentals, history), news/filings sources.

**The tool-calling contract (conversation layer ↔ deterministic engine).** The conversation layer never computes a financial figure itself. It calls a fixed set of typed tools (e.g. `get_position(symbol)`, `compute_portfolio_metrics(metrics[])`, `run_backtest(strategy_id, date_range)`), each backed by a real function in `/backend/analysis`, `/backend/backtest`, or `/backend/risk`. The function runs against live data and returns structured output (numbers, not prose) with a timestamp. The LLM then writes the natural-language answer, grounded in — and only in — what the tool returned. Register each tool next to the function it wraps (name, argument schema, one-line description) so adding a capability is a one-line registration, not a prompt-editing exercise. This is what makes every KUBERA answer traceable to a specific function call with specific inputs.

## 4. Recommended tech stack

Strong, current (mid-2026) defaults — Phase 0's job is to confirm or override these and record the decision in `DECISIONS.md`, not to relitigate every choice from scratch.

- **Backend:** Python + FastAPI. Best-served ecosystem for the data/quant/backtesting work, async-friendly for streaming quotes.
- **Frontend:** Flutter. One codebase genuinely targets iOS, Android, Windows desktop, and web — three separate native apps is three times the surface area to keep in sync for no real benefit at this stage. Revisit only if a platform-specific capability in §6 forces a native module.
- **Database:** PostgreSQL, with the `pgvector` extension for KUBERA's research memory instead of running a second database system. Redis for a real-time quote cache.
- **Broker / execution:** Alpaca is the easiest starting point — commission-free, a genuinely free real-time paper-trading environment (not a delayed simulation), and an API built for exactly this kind of project. Charles Schwab's Trader API is a solid alternative if you'd rather trade through an account you already hold at a full-service broker — free with a brokerage account, though the developer-portal setup is more involved. Either way: build against the paper endpoint first and don't touch the live endpoint until §7.4's gate is satisfied.
- **Backtesting:** Start with `vectorbt` or `backtrader` for fast iteration in Phase 3. If you outgrow it — multi-asset strategies, wanting backtest/live parity, managed live deployment — QuantConnect's open-source LEAN engine is the strongest actively-maintained option in this space and is self-hostable if you'd rather skip the cloud subscription.
- **Market data:** Alpaca's own Market Data API covers real-time and historical US equities and is bundled with the brokerage relationship. For deeper fundamentals/history, Tiingo or Financial Modeling Prep are current, well-regarded options. Don't build against IEX Cloud — it shut down in August 2024; a lot of older tutorials still reference it.
- **Vector store:** `pgvector`, to avoid standing up a separate vector database for what is, at this scale, a modest amount of research memory.
- **Voice (Phase 5+):** cloud STT/TTS to start (fast to integrate, high quality); revisit on-device options per platform once the voice layer is proven useful.
- **Infra:** Docker for reproducibility, GitHub Actions for CI, a small managed host for the backend (Fly.io/Railway/a basic cloud VM — pick one in Phase 0 and log why in `DECISIONS.md`).

## 5. Your multi-agent team

You don't need all four tools on every task, and you don't need to guess who does what — here's a starting division of labor. Any of you can pick up any `TASKS.md` item; this is about playing to strengths, not a rigid assignment.

- **Claude Code** — primary implementer for the deterministic engine (`/backend/analysis`, `/backend/risk`, `/backend/backtest`) and code review on anything another agent produced. This is the code where correctness matters most.
- **Gemini, inside Antigravity** — orchestrator. Antigravity's Agent Manager runs and observes several async agents across the editor, terminal, and browser at once, and keeps its own "knowledge items" from past runs. Use it to drive the overall task list, scaffold new modules, and do browser-verified frontend work (it can drive a real browser to click through the Flutter web build and confirm a feature actually works). Antigravity also offers model choice inside the agent — check what's currently available if you'd rather point a given task at a different model.
- **GitHub Copilot** — in-editor completion while you or another agent is actively reviewing, plus its coding agent mode for small, well-defined `TASKS.md` items assigned as GitHub issues (add tests for a module, fix a lint pass, write a migration) that can run in parallel with whatever Claude Code or Antigravity is doing.
- **ChatGPT (Codex)** — algorithm and strategy brainstorming, research synthesis for the research agent's proposals, and an independent second opinion on architecture decisions before they're written into `DECISIONS.md`. A different model reviewing a decision catches different blind spots than the model that made it.

Whoever's driving, the contract is the same: read `AGENTS.md` and the memory files at the start, update them at the end. That's what makes the tools interchangeable instead of each needing you to re-explain the project.

## 6. Voice & cross-platform: what's actually possible today

This directly affects how you sequence Phases 5–6 — being honest about it now saves a rebuild later.

- **iOS.** Apple deprecated SiriKit in 2026 in favor of App Intents, now the only way a third-party app talks to Siri — and substantially more capable than the old canned-phrase Shortcuts model: multi-step intents, streaming responses for long-running actions, on-screen awareness. Practically, "Hey Siri, ask KUBERA how my portfolio's doing" is a realistic, well-supported target once you build the App Intents for it. A true independent always-listening "Hey KUBERA" background wake word is a different capability (system-level background microphone access for a third-party process) and stays restricted the way it's long been on iOS. Apple has also signaled tighter Siri restrictions specifically around banking/financial apps — re-check current App Intent policy for finance apps when you reach Phase 6, since that's exactly KUBERA's category.
- **Android.** Google Assistant has been replaced by Gemini. Third-party voice integration now runs through Android's "App Functions" framework and "Gemini Extensions" — you register the actions KUBERA can perform and Gemini calls them. As of mid-2026 deep hooks (custom wake words, background execution) have mostly been Gemini-exclusive, but a July 2026 EU Digital Markets Act ruling now requires Google to open those exact hooks to third-party assistants on equal terms. It's very recent and still rolling out — check the current state when you get to this phase.
- **Windows.** The least restrictive of the three — a background tray app with its own wake-word listener (an open-source engine like openWakeWord, or a licensed one like Picovoice Porcupine) is straightforward and doesn't depend on a platform vendor's assistant integration.

**Recommended sequencing:** ship push-to-talk voice inside the app first (Phase 5 — identical on all three platforms, no platform-specific hands-free work). Add Siri App Intents (iOS) and a Windows tray listener next, since both are well-supported today. Treat Android hands-free as a Phase 6 stretch goal pending how the DMA-driven access actually rolls out.

## 7. Phased roadmap

Each phase lists its goal and what "done" looks like. Break each phase into `TASKS.md` tickets small enough to finish in one focused agent session — "build Phase 2" is not a task; "add Sharpe ratio and max-drawdown calculation with unit tests" is.

### Phase 0 — Foundations
Repo scaffolding, `AGENTS.md` and `/project-memory/` live, CI running on a trivial test, secrets management in place (`.env` + `.gitignore`, a secret-scanning pre-commit hook), and the Phase-0 decisions in §4 confirmed and logged to `DECISIONS.md`: broker, data provider, hosting.
**Done when:** a new agent can clone the repo, read `AGENTS.md`, and know what to do next without asking you anything. CI is green. No secret has ever touched git history.

### Phase 1 — Data & portfolio backbone
Broker integration (paper account first), real position/balance sync, market data ingestion, the core database schema, scheduled refresh jobs.
**Done when:** KUBERA can answer "what do I hold and what's it worth right now" with live numbers, tested, with zero mock data in the code path.

### Phase 2 — Analysis & insight engine
Deterministic metrics (returns, CAGR, volatility, Sharpe, drawdown, sector/concentration exposure, a win/loss breakdown across positions), benchmark comparison against the S&P 500 and other indices/ETFs, fundamentals and news ingestion, short-horizon (technical) and long-horizon (fundamental) framing on the same question, and the tool-calling layer from §3.
**Done when:** "Is buying $X of TICKER a good idea right now" returns analysis grounded in real, cited, computed numbers, with stated assumptions and risks — not false confidence.

### Phase 3 — Backtesting & strategy sandbox
Backtesting engine wired to historical data, a small library of strategy templates, a paper-trading loop that runs candidates against live data with results logged, dashboards comparing candidates to the benchmark and each other.
**Done when:** every strategy has a repeatable, automated way to pass or fail the §7.4 promotion checklist.

### Phase 4 — Conversational layer (text-first)
KUBERA's own persona and system prompt (precise, always states data recency and confidence, never invents numbers), retrieval over portfolio state + research memory + recent conversation, the §3 tool-calling contract into Phase 2/3's functions, conversation-level safety rails (confirms before anything touching live capital).
**Done when:** you can have a real back-and-forth — "how's my portfolio doing against the market this quarter," "should I be worried about my tech exposure" — and get accurate, current, well-reasoned answers in chat, on any device.

### Phase 5 — Cross-platform app & push-to-talk voice
Ship the Flutter client to iPhone, Android, and Windows: chat UI, dashboard, benchmark charts, notifications, plus in-app STT/TTS.
**Done when:** you can open the app on any of the three, tap the mic, ask a question, and hear a spoken, accurate answer, with the dashboard current.

### Phase 6 — Hands-free integration
Per §6: Siri App Intents on iOS, a Windows tray listener, Android hands-free as available.
**Done when:** hands-free invocation works within each platform's real constraints, documented so expectations match reality.

### Phase 7 — Continuous learning loop (human-gated)
**7.4 — the promotion checklist, referenced throughout this document:** a strategy or strategy change may only reach live capital after (a) backtesting across multiple market regimes, (b) a minimum paper-trading period you define (e.g. 60–90 days) meeting stated drawdown/return criteria, and (c) your explicit, specific approval — not a standing permission. Every promoted strategy keeps a version history so you can roll back.
The research agent runs on a schedule, monitors news/market conditions/new techniques, and writes proposals into the Phase 3 sandbox. It never has write access to the risk engine or the broker connection.
**Done when:** KUBERA gets better over time in a way you can audit and roll back — never silently.

### Phase 8 — Hardening & ongoing ops
Monitoring and alerting (errors, data feed outages, circuit-breaker trips), a security pass (key rotation, least-privilege scopes, 2FA everywhere), database backups, cost monitoring, a short runbook for incidents like "the data feed is down" or "a strategy tripped the circuit breaker."

## 8. Safety rails specification

Concrete defaults for `/backend/risk` — tune the numbers to your own risk tolerance in Phase 0/7, but keep the mechanism:
- Max position size as a % of portfolio, enforced per order, not just recommended.
- Daily loss circuit breaker: trading halts automatically (paper or live) past a defined daily drawdown, requiring manual reset.
- Every order request carries a pre-trade check against both limits; a failed check blocks the order before it reaches the broker, full stop.
- Live-capital orders below a certain size can be pre-authorized per strategy per §7.4; above it, always require a fresh confirmation.

## 9. Testing & definition of done

- CI runs the full test suite on every push; no agent marks a task done, and no PR merges, unless CI is green.
- `/backend/analysis` and `/backend/risk` need unit tests for every function before they're complete — these are the modules where a silent bug costs real money.
- Broker and market-data integrations get integration tests against the paper/sandbox environment, not just mocks.
- A strategy doesn't reach even paper trading without a backtest across more than one market regime (e.g. not just the last 12 months).

## 10. Regulatory notes

Not legal advice — factual context, not a substitute for a lawyer if you want specifics. Trading your own capital through your own brokerage account via an API you control is routine; individuals do this without special licensing. The line that matters: managing money on behalf of *other* people typically triggers investment adviser and/or broker-dealer registration requirements. This build is scoped to your own account, and this spec should not be extended to manage anyone else's money without a securities attorney's input first. Separately, respect your broker's and data provider's terms of service around automated trading and data redistribution — using their official APIs as intended, as this spec does throughout, keeps you inside those terms.

## 11. project-memory/ file templates

Create these in Phase 0. Keep each one short — a running log, not an archive; move old entries to `/project-memory/archive/` when a file gets long.

**PROGRESS.md**
```
## 2026-08-10 — Claude Code
Built: position sync from Alpaca paper account, position table schema.
Next: return/volatility calculations in /backend/analysis.
Blockers: none.
```

**TASKS.md**
```
## In progress
- [ ] T014 — Sharpe ratio + max drawdown calc (owner: Claude Code)

## Backlog
- [ ] T015 — benchmark comparison vs SPY

## Blocked
(none)

## Done
- [x] T013 — position sync from Alpaca — 2026-08-09 — a1b2c3d
```

**DECISIONS.md**
```
## D003 — Broker: Alpaca over Schwab (2026-08-08)
Chose Alpaca for the free real-time paper environment and simpler API auth.
Revisit if we need asset classes Alpaca doesn't support.
```

**ISSUES.md**
```
## I007 — Paper account balance not resetting via API
Repro: POST /paper/reset returns 200 but balance unchanged.
Status: open, worked around by resetting in dashboard.
```

## 12. Session kickoff template

Paste this into any tool, any time, to start a session:

> Read `/AGENTS.md`, then `/project-memory/PROGRESS.md`, then pick up the top unblocked item in `/project-memory/TASKS.md` that fits your strengths. If none fit, tell me what's blocked and why instead of picking an unrelated task.
