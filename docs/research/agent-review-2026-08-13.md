# Cross-agent review — 2026-08-13 (binding dispositions: D018)

*Source: review document the owner uploaded (authored in another AI session against
our own project-memory files; header credits Gemini/Antigravity). Original preserved
by the owner; this file records the DISPOSITIONS. Owner directive attached to the
upload: Schwab (T016) stays deferred — approval still pending; continue on Alpaca.*

## Overall verdict
The most useful review yet, because it read our actual repo state: its "already
excellent, don't change" list is accurate, roughly 70% of its suggestions were
already ticketed (it functions as a priority vote), and it found four genuinely new,
small, high-value items — three of which were BUILT the same session (see below).

## Built immediately (this session)
- **2.3 Stale-data detection** → `MAX_DATA_AGE_SECONDS=900` in the market client;
  every latest trade/quote now carries `age_seconds` + `stale`; get_latest tool
  description orders the model to never present stale data as live. Note: outside
  market hours data reads stale BY DESIGN — "this price is from Friday" is the
  honest answer. (Market-hours awareness arrives with T036's guard.)
- **5.4 Database backups** → `scripts/backup_db.py`: timestamped copies, --keep
  retention (default 14), backups/ git-ignored, Task Scheduler one-liner in the
  docstring. Fails closed on missing DB.
- **5.1 Health monitoring** → `scripts/health_check.py`: server reachable, breaker
  tripped (read from risk_state, works with the server down), snapshot freshness;
  exit code + best-effort Windows toast (--notify). Freshness is wall-clock, not
  market-hours — documented.

## Priority votes on existing tickets — accepted into TASKS guidance
T052 intraday (the doctrine's backbone) → T055 no-trade (overtrading is the owner's
stated failure mode) → T077 expected-move → T067 DQS / T062 briefs. "More strategy
templates before T055 = more overtrading" — agreed; T054's router work should land
WITH T055's no-trade taxonomy, not before it.

## Enrichments folded into existing tickets
- **1.3 → T064**: concrete promotion mechanics — ledger gains `promotion_status`
  (pending / passed_walk_forward / eligible) and the paper loop refuses templates
  that haven't passed out-of-sample. Good design; adopted verbatim.
- **4.2 → T063**: journal must capture the pre-decision context (regime label +
  confidence, thesis from chat, recommendation) AND whether the owner followed or
  OVERRODE it — override-rate vs outcome is the measurable behavioral pattern.
- **3.4 → T036**: entry-timing ("never the open-print buyer") joins the
  market-hours guard: configurable entry delay after the open, default preserving
  current behavior.
- **1.1 → T016**: owner directive recorded — Schwab approval pending, Alpaca
  continues; ticket stays parked as an owner action, not agent-blocked.
- **3.3 → T079**: correctly observed it is NOT blocked by T023 — daily-bar
  correlation math needs no sector tags. Unblocked in the ticket text; sector caps
  remain the T065/T023 half.
- **2.1 → T082 (new)** + notes: feed-quality labels already exist end-to-end in the
  data payloads (source, volume_feed, D006 notes); the remaining gap is SURFACING
  them in the Orb UI — folded into T082.

## New ticket
- **T082 — Orb upgrade pack** (6.1 + 6.2 + 2.1 surface): conversations sidebar
  (needs a small `GET /api/conversations` list endpoint — only /api/chat/{id}
  exists), collapsible portfolio snapshot panel (auto-refresh /portfolio), and
  visible feed-quality/stale badges on quoted numbers. UI-heavy — flagged as a
  strong Gemini/Antigravity ticket per AGENTS.md strengths.

## Deferred with reasons (not silently dropped)
- **5.2 Postgres now**: disagree on the trigger. Current write volume (hourly paper
  cycles + chat rows) is trivial for SQLite; D007's real trigger is pgvector for
  Phase 7 memory or T052's minute-bar STORAGE if we persist it. Revisit at T052
  build time with actual row-rate numbers — not before evidence.
- **1.2 T060 "benchmark is mathematically wrong"**: correct in principle, softened
  in fact — the owner's paper account has had no external flows yet, so current
  curves are not yet distorted. T060 rises in priority the day a deposit happens;
  noted on the ticket rather than jumping the doctrine queue.
- **6.3 T072 TTS**: agreed it's cheap and high-feel; left in queue order because
  edge-tts (shipped) already covers "not robotic" — T072 is the upgrade from good
  to great, not from broken to working.
