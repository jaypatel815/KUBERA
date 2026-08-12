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

Let a strategy trade your **paper** account (migrate the DB first — see above):

```
python scripts\paper_trade.py SPY --strategy momentum              # one cycle
python scripts\paper_trade.py SPY --strategy momentum --loop 3600  # hourly, Ctrl+C to stop
```

Each cycle: strategy reads real bars → target position → **fail-closed risk gate** (20%
per-symbol cap, 3% daily-loss circuit breaker) → market order on the paper account. Every
decision — ordered, rejected, or no-action — is written to the `signal_log` table with the
data snapshot it was based on. Strategies: momentum, sma_cross, mean_reversion, buy_and_hold.
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

**Talk to KUBERA out loud** (server running, then in a second terminal):

```
pip install -r requirements-voice.txt      # once; audio deps stay out of the backend
python scripts\talk.py                     # Enter = talk, Enter again = stop, q = quit
```

Local Whisper transcribes you; Windows' voice speaks the reply. **The default voice is
robotic — fix it:** `pip install edge-tts soundfile`, then `set KUBERA_TTS=edge` for
neural voices (`set KUBERA_VOICE=en-US-AndrewNeural` is the most natural; Guy is the
default, Aria for a female voice). `KUBERA_STT=openai` if local Whisper won't install.
Replies come back voice-shaped: no tables, numbers rounded for the ear. Typing `confirm`
before a turn is the ONLY way to send a confirmed request — saying "yes" never is.

Run the full test suite any time: `python scripts\verify.py` (190+ tests; a few live ones
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
