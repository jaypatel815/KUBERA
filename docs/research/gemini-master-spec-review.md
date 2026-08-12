# Gemini master-spec review — reconciliation (2026-08-12)

*Companion to `chatgpt-master-spec-review.md` (D013). Shared rejections (microservice/
Kafka stack, agent bureaucracy, 25-document suites, options/crypto domains) are NOT
re-argued here — the D013 reasoning applies verbatim. This review covers what is NEW in
the Gemini spec. Binding record; see D014.*

## The standout adoption: the Quantitative Trading Coach

Gemini's best idea, absent from both our build and the ChatGPT spec: KUBERA as a
continuous coach for the OWNER'S OWN trading — not just a recommender.

Core principles adopted verbatim into doctrine:
- **Process over outcome**: "a profitable trade can still be a poor decision if it
  violated sound investment principles; a losing trade can be a good decision if it
  followed a disciplined process." Decisions are judged on the information available at
  entry time.
- **Never validate to please**: respectfully challenge assumptions; identify emotion-
  driven trades; recommend better alternatives; criticism is part of the job.
- **Decision Quality Score** (the owner's own enhancement): combine risk-budget-consumed
  with behavioral quality, so intervention triggers on *impulsive-but-profitable* days
  and relaxes on *disciplined-but-losing* days. Levels: advisory → caution → strong
  warning → pause recommendation (Level 4's hard version already exists: the breaker).
- **Behavioral pattern detection**: revenge trading, FOMO, averaging down excessively,
  selling winners early / holding losers long, overtrading, post-loss and post-win
  impulsivity.

Prerequisite: T016 (Schwab/thinkorswim read-only sync) — coaching needs his real fills.
Until then, chat-level coaching applies when the owner describes his trades (persona
now instructs this).

## Adopted as tickets

- **T066** — Trade coaching pack: pre-trade review (thesis/sizing/concentration/
  correlation/regime fit vs the IPS) + post-trade review (expected vs actual, entry/exit
  quality, rule adherence, lesson) persisted per trade; process-not-outcome scoring.
  Depends on T016; chat-level v0 works via conversation.
- **T067** — Decision Quality Score + graduated risk advisories: rolling DQS from
  behavioral signals + risk-budget-consumed; advisory levels 1–3 as proactive messages
  (Level 4 hard stop = existing breaker, unchanged); daily risk budget derived from the
  IPS. Extends signal_log/journal.
- **T068** — Watchlist + opportunity ranking: watchlist table; ranked view scoring
  briefings (edge, risk, portfolio fit, confidence) — the "ranked research pipeline"
  instead of isolated ideas.

## Upgraded existing tickets

- **T061** → now "User profile + Investment Policy Statement (IPS)": objectives, target
  return, max acceptable drawdown, horizon, restrictions, prohibited strategies — every
  recommendation checked against it (Gemini's IPS is the richer version of the profile).
- **T062** → briefs now include the **weekly investment-committee review** (performance,
  discipline, behavioral trends, lessons, next week's priorities).
- **T064** → backtest rigor now includes **named historical-crisis windows** (2008,
  2020, 2022 at minimum, given data availability) as standard stress runs.

## Adopted into persona now (code)

- Coaching rule: judge the user's trading decisions by process quality, not outcome;
  say plainly (with evidence) when a decision looks emotional or unsupported.
- Educational mode: when asked why, teach the underlying concept at the level of
  someone learning quantitative investing.

## Logged to the research backlog (not ticketed)

Confidence decomposition (needs multiple models to decompose — Phase 7), performance
attribution by factor (needs factor data), Independent Challenge Agent as a second-model
pass (our persona's mandatory case-against + the multi-agent review process covers v1),
model governance registry (when ML models exist), Kelly/HRP/Black-Litterman portfolio
optimizers (research queue via §7.7), tail-hedging instruments (options domain is
warn-only per doctrine).

## Self-exclusion doctrine (owner request, 2026-08-12 — built + honest limits)

The owner described blowing through his own risk limits and continuing to trade. Adopted:

1. **Time-locked breaker reset (BUILT)**: when the breaker trips, `risk_reset.py` refuses
   for `cooldown_hours` (default 20h). No override flag exists — deliberately. Tests
   prove the lockout survives restarts and refuses one minute before expiry.
2. **Honest limits, on the record**: KUBERA cannot freeze the owner's thinkorswim
   account — no third-party software is in that path; and any lockout on a machine the
   owner administrates is strong friction, not cryptography. Do not promise otherwise.
3. **Structural answer**: the durable fix is allocation — KUBERA-managed capital (rails
   are code, §7.4-gated) large, self-directed account deliberately small. Broker-side
   friction the owner can add himself: remove the phone app, no saved logins, cash
   account (settlement throttles), keep long-term holdings in a separate account.
4. **T069**: KUBERA estimates the risk budget from account composition + behavior,
   because in-the-moment self-assessment is the thing that fails.

## Rejected (D013 reasoning applies)

ML/DL/RL model zoo now (every model enters through the §7.7 research pipeline with
walk-forward validation, never direct deployment — which Gemini's own spec agrees with);
22 named sub-agents; tick/L2/satellite/alt-data ingestion at single-user scale; the
25-document governance suite (project-memory + this review process IS that system,
demonstrated daily); "thousands of securities" scanning before the data tier supports it.
