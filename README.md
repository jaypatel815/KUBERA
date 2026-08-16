# KUBERA

A personal financial research and portfolio-management assistant, built 100% by AI agents
with a human product owner. Personal use, own capital only — not investment advice, not an
RIA (see `/project-memory/PROJECT_SPEC.md` §10).

## Resume a session (any agent, any tool)

Paste this into Claude Code, Antigravity/Gemini, Copilot, or ChatGPT:

> Read `/AGENTS.md`, then `/project-memory/PROGRESS.md`, then pick up the top unblocked item
> in `/project-memory/TASKS.md` that fits your strengths. If none fit, tell me what's blocked
> and why instead of picking an unrelated task.

In Claude Cowork: select this folder and type `/kubera`.

## Quickstart (Windows)

```
py -3.14.7 -m venv .venv
.venv\Scripts\activate
pip install -r backend\requirements.txt
python scripts\verify.py          # lint + tests — must PASS
uvicorn --app-dir backend api.main:app --reload
```

Then open http://127.0.0.1:8000/health — a JSON `"status": "ok"` means the backbone is alive.

With Alpaca paper keys in `.env`, create the database and take a snapshot:

```
alembic -c backend\alembic.ini upgrade head
python scripts\sync.py            # add --loop 300 to snapshot every 5 minutes
```

## Try what's built so far

With the server running (`uvicorn --app-dir backend api.main:app --reload`), open these in a browser:

```
http://127.0.0.1:8000/docs                                  interactive API explorer (try everything from here)
http://127.0.0.1:8000/health                                liveness + whether your keys are detected
http://127.0.0.1:8000/portfolio                             live paper account: positions, totals, win/loss
http://127.0.0.1:8000/api/account                           equity, cash, buying power (timestamped)
http://127.0.0.1:8000/api/market/AAPL/latest                latest trade + bid/ask for any symbol
http://127.0.0.1:8000/api/market/AAPL/bars?days=30          daily price history (split-adjusted)
http://127.0.0.1:8000/api/briefing/AAPL                     "should I buy X" evidence pack: momentum,
                                                            volatility, drawdown, 52-week position, trend,
                                                            your current exposure — facts only, dated
http://127.0.0.1:8000/api/benchmark?symbol=SPY&days=90      your equity curve vs the market (needs snapshot
                                                            history — run sync daily so this gets richer)
http://127.0.0.1:8000/api/regime/SPY                        what kind of market is this? trending / range-bound /
                                                            breakout-watch, with swing structure, range width
                                                            percentile, RVOL and fakeout suspicion — all evidence
                                                            shown, feed labeled, never certain
http://127.0.0.1:8000/api/levels/SPY                        where are support and resistance? clustered swing
                                                            rejections with touch counts (2 touches make a level,
                                                            5 make a strong one) + nearest edge above and below
http://127.0.0.1:8000/api/breakouts/SPY                     did it break out — and did the break HOLD? every
                                                            escape judged on volume + hold: confirmed, failed
                                                            (fakeout completed), unconfirmed, or pending
http://127.0.0.1:8000/api/intraday/SPY                      what kind of day is it SO FAR? session VWAP with
                                                            price side + crossings (churn = no trend), and
                                                            intraday RVOL — today's volume at this point vs
                                                            the same point on prior days
http://127.0.0.1:8000/api/expected-move/SPY?horizon_days=5  how far does it usually travel in N days? percentile
                                                            bands (in % and price), historical win rate, payoff
                                                            ratio, conditioned on the current volatility regime.
                                                            Ranges, never targets — the past, not a forecast
http://127.0.0.1:8000/api/risk                              your risk dashboard: daily loss budget consumed,
                                                            current tier (1 stricter → 2 half-size → 3 paused →
                                                            4 breaker), lockout state, and your Decision Quality
                                                            Score — process over outcome
http://127.0.0.1:8000/api/brief?type=morning                your day, composed: overnight gaps (staleness
                                                            flagged), regime + expected move + nearest levels
                                                            per holding, risk status. Also type=eod (today's
                                                            decisions + reasons) and type=weekly (you vs SPY,
                                                            discipline, lessons). Best enjoyed by voice: ask
                                                            the Orb "give me my morning brief"
http://127.0.0.1:8000/api/macro                             the macro weather: yield-curve inversion, VIX
                                                            bucket, real rates, fed funds — cautionary signals
                                                            counted, each series dated. Needs a free
                                                            FRED_API_KEY in .env (link in .env.example)
http://127.0.0.1:8000/api/journal                           the decision journal: every recommendation KUBERA
                                                            made (with regime, entry, target, stop at decision
                                                            time), whether you followed or overrode it, and
                                                            direction-hit calibration once entries age
http://127.0.0.1:8000/api/confluence/SPY                    do the timeframes agree? daily + hourly regimes +
                                                            session VWAP side vote on the daily read — agreement
                                                            strengthens confidence, conflict and churn weaken it,
                                                            the call itself never flips
http://127.0.0.1:8000/api/exit-plan/SPY                     how long do I hold? invalidation level, target
                                                            (ranges only — trends are ridden, not targeted),
                                                            review clock, stop distance in ATRs, reward/risk —
                                                            the plan keyed to WHY you'd be in the trade
http://127.0.0.1:8000/api/size/SPY                          how many shares could I buy RIGHT NOW? exact qty
                                                            from your equity, the ATR stop, cap headroom, and
                                                            the current risk tier — with the stop price and
                                                            what limited it. Zero when entries are paused
http://127.0.0.1:8000/api/triage/SPY?entry_price=640        I'm IN the trade — hold, exit, or add? judged
                                                            against the live exit plan; averaging down is never
                                                            called "lowering your average" — range adds only at
                                                            the edge, trend adds only on strength
http://127.0.0.1:8000/api/attribution                       WHY is the money moving? realized P&L by regime,
                                                            router leg, and time-of-entry — each round trip
                                                            credited to the conditions that OPENED it; your
                                                            manual trades show as "unattributed"
http://127.0.0.1:8000/api/tools                             the tool registry the chat layer will use
http://127.0.0.1:8000/api/backtests                         the results ledger: every recorded backtest
POST /api/backtests/run?strategy=momentum&symbol=SPY        run + record a backtest (use /docs to click it)
POST /api/chat            {"message": "how is my portfolio doing?"}   — TALK TO KUBERA
GET  /api/chat/{id}                                         full audit trail of a conversation
```

**Talking to KUBERA** — pick ONE brain via `LLM_PROVIDER` in `.env`:

- `claude-sdk` — **your Claude Max subscription, no API credits** (personal use only,
  see DECISIONS D012). One-time setup: `pip install claude-agent-sdk`, run
  `claude setup-token` (logs into your Claude account), put the token in `.env` as
  `CLAUDE_CODE_OAUTH_TOKEN`. Shares your Max weekly limits with Claude Code/Cowork.
- `openai` + `OPENAI_BASE_URL=http://localhost:11434/v1` — free local via Ollama
  (validated with `nemotron-3.5-lightning`); or real OpenAI with `OPENAI_API_KEY`.
- `anthropic` — Anthropic API with `ANTHROPIC_API_KEY` (needs API credits).

Then open `/docs`, expand `POST /api/chat`, "Try it out", and ask *"Should I buy more
AAPL?"* — KUBERA calls its tools and answers with sourced, dated numbers. Reuse the
returned `conversation_id` to continue the thread.

Backtest the strategy templates on real history (no server needed):

```
python scripts\backtest_demo.py                 # SPY, ~2 years: buy-and-hold vs momentum vs
python scripts\backtest_demo.py AAPL --days 365 # SMA-cross vs mean-reversion, with costs
```

Let a strategy trade your **paper** account (migrate the DB first — see above).
**Strategies must EARN the loop:** run the walk-forward promotion gate first — it
backtests the pair on real history and only a pass unlocks new buys (sells always work):

```
python scripts\promote.py regime_router SPY     # PASS/FAIL + per-segment returns
python scripts\paper_trade.py SPY --strategy regime_router              # one cycle
python scripts\paper_trade.py SPY --strategy regime_router --loop 3600  # hourly
```

An unpromoted pair gets a logged `no_trade` ("promotion gate") instead of orders —
`--skip-promotion-gate` exists, but using it defeats the point.

The loop also respects the clock: a closed market means no orders (nothing queues
for the open print), and new buys wait out the first 30 minutes after the open
(doctrine; `--entry-delay 0` disables, `--after-hours` bypasses the guard). Sells
are never delayed. `scripts\sync.py` now also pulls your executed fills into the
database each run — the ground truth behind slippage and attribution reports.

Each cycle: strategy reads real bars → **no-trade check** (overtrading guard: max 5
orders/day; expected move vs cost floor; quiet-market check — low RVOL in a tight
range means the market isn't interested; "there isn't a trade today" is a logged,
first-class decision) → **volatility-parity sizing** (a buy may risk at most 1% of
equity if its 2×ATR stop is hit; sells are never blocked by any of this) →
**fail-closed risk gate** (20% per-symbol cap, 3% daily-loss circuit breaker) →
market order on the paper account. Every decision — ordered, rejected, no-action, or
no-trade — is written to the `signal_log` table with the data snapshot it was based
on. Strategies: momentum, sma_cross, mean_reversion, buy_and_hold, **range** (trades
only the edges, refuses trends), and **regime_router** — the meta-strategy that first
asks "what kind of market is this?" and then picks momentum, range trading, or cash.
Paper only: there is deliberately no code path to real money.

The circuit breaker persists to the database — restarting the loop cannot bypass a trip.
If it trips, inspect and (deliberately, with a note) reset it:

```
python scripts\risk_reset.py                                  # show current risk state
python scripts\risk_reset.py --note "reviewed the drawdown"   # reset (asks you to type RESET)
```

**Cooling-off lockout:** after a trip, the reset is refused for ~20 hours (configurable
via `RiskLimits.cooldown_hours`). There is no override flag — that's the feature: the
person who set the limit shouldn't be able to remove it in the moment it starts hurting.

**The KUBERA Orb** — the voice-first web interface. Install the server-side voice once
(`pip install edge-tts` in the venv), start the server, then open **http://127.0.0.1:8000/**
in Chrome or Edge. Click the orb (or hold Space) and talk; it turns teal listening, violet
thinking, gold speaking — with chips showing which tools it used. Type in the box if you
must; tick "confirm this turn" for confirmation-gated actions (that tick is the deliberate
gesture — saying yes is not).

Two collapsible side panels (T082, 2026-08-16):
- **☰ (top-left)** — conversation history: all past threads sorted by last activity, each
  showing your opening words. Click any thread to resume it; the next message continues
  that conversation. "**+ new**" starts a fresh thread.
- **▣ (top-right)** — live portfolio snapshot: equity, day P&L, and your top-3 positions by
  value, refreshed every 60 seconds while the panel is open. Shows "broker offline" if
  Alpaca is unreachable.
- Tool chips from `get_latest` / `get_symbol_briefing` show a **teal border** during RTH
  (the data is live) and **gold** outside it (last session — trustworthy, not live).

**Talk to KUBERA in the terminal instead** (server running, then in a second terminal):

```
pip install -r requirements-voice.txt      # once; audio deps stay out of the backend
python scripts\talk.py                     # Enter = talk, Enter again = stop, q = quit
```

Local Whisper transcribes you; Windows' SAPI speaks the reply by default.
**The voice quality ladder (set `KUBERA_TTS` + optional `KUBERA_VOICE`):**
- `sapi` (default) — Windows built-in, robotic, zero extra dependencies.
- `edge` — Microsoft neural voices (free, online): `pip install edge-tts soundfile`, `set KUBERA_TTS=edge`, `set KUBERA_VOICE=en-US-AndrewNeural` (Guy is default, Aria for female).
- `openai` — OpenAI TTS API (near-human, ~$0.015/1k chars): `pip install openai soundfile`, `set KUBERA_TTS=openai`, `set KUBERA_VOICE=alloy` (or `nova`, `onyx`, `fable`; `KUBERA_OPENAI_TTS_MODEL=tts-1`). Needs `OPENAI_API_KEY`.
- `kokoro` — local near-human neural voice (free, offline, 50+ voices): `pip install kokoro-onnx soundfile`, place `kokoro-v1.0.onnx` + `voices-v1.0.bin` in `models/kokoro/` (or set `KUBERA_KOKORO_DIR`), `set KUBERA_TTS=kokoro`, `set KUBERA_VOICE=af_heart`.

`KUBERA_STT=openai` if local Whisper won't install on your Python version.
Replies come back voice-shaped: no tables, numbers rounded for the ear. Typing `confirm`
before a turn is the ONLY way to send a confirmed request — saying "yes" never is.

**Keep it safe on autopilot** (each docstring has the Task Scheduler one-liner):

```
python scripts\backup_db.py                # timestamped DB backup, keeps newest 14
python scripts\health_check.py --notify    # server up? breaker tripped? sync fresh?
                                           # exit 1 + Windows toast on problems
```

Every live quote now carries `age_seconds` and a `stale` flag (older than 15 min —
normal outside market hours): KUBERA is told to never present stale data as live.

Run the full test suite any time: `python scripts\verify.py` (280+ tests; a few live ones
run only when keys + internet are available). If local Python ever breaks:
`powershell -ExecutionPolicy Bypass -File scripts\repair_python.ps1`.

## Repo map

- `/AGENTS.md` — the contract every AI agent follows. Read first, always.
- `/project-memory/` — shared memory: spec, progress, tasks, decisions, issues.
- `/backend/` — FastAPI app (`api`), deterministic engine (`analysis`, `risk`, `backtest`),
  data layer (`data`), scheduled research process (`research_agent`), tests.
- `/apps/` — PWA client (Phase 5).
- `/scripts/verify.py` — the one gate: green before any session ends. CI runs the same script.

## Status

Current phase and next steps: `/project-memory/PROGRESS.md` (newest entry on top).
Roadmap: `/project-memory/PROJECT_SPEC.md` §7. Phases: 0 Foundations · 1 Data & portfolio ·
2 Analysis engine · 3 Backtesting · 4 Conversation · 5 Cross-platform app + voice ·
6 Hands-free · 7 Continuous learning · 8 Hardening.
