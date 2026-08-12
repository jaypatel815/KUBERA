# ChatGPT master-spec review — reconciliation with the live KUBERA (2026-08-12)

*The owner's pre-project ChatGPT specification (master prompt + Software Factory) was
reviewed section-by-section against the current repo. Verdict per item: ALREADY BUILT,
ADOPTED (new ticket/change), or REJECTED (with reason). This document is the record —
do not re-litigate items here without new evidence. Note: that spec's §43 stack matches
the extra vars in the owner's .env — it was the abandoned first attempt (see D009).*

## Already built (no duplication — verified equivalents)

| ChatGPT spec | Our implementation |
|---|---|
| Identity/personality (§1–3) | `api/persona.py` CORE_RULES + spec §1–2 (upgraded further today — see ADOPTED) |
| Live-data-only, timestamps (§4) | AGENTS.md priority #1; asof on every payload; T043 recency post-check |
| No fabricated certainty (§11) | Persona rules 1/3/4; guard tests |
| LLM never controls execution (§14) | Registry + risk gate + paper loop; LLM physically outside the order path |
| Modular strategies (§15) | `TEMPLATES` registry; no hard-coded "KUBERA strategy" |
| Backtest → paper progression (§17) | Spec §7.4 promotion checklist; ledger as evidence base |
| Risk engine authority + kill switch (§18) | Fail-closed RiskEngine; breaker = kill switch; DB-persisted; human-only reset |
| Approval modes (§19) | Research/recommend = chat; paper = loop; Mode-4 confirmation = T043 gate; Mode 5 gated by §7.4; Mode 6 = tripped breaker |
| Explainability (§38) | signal_log + chat_messages audit; "why did KUBERA do that" is a SELECT |
| Regime engine (§36) | T050–T056 pack (owner's own doctrine, more concrete than the spec's version) |
| Continuous-learning pipeline w/ human gate (§26) | Spec §7.7 — identical philosophy |
| Software Factory (repo-as-memory, handoffs, state files, CI, failure routing, verification-not-trust) | AGENTS.md + project-memory/ (PROGRESS=state+handoffs, TASKS=queue, DECISIONS=ADRs, ISSUES=lessons/pitfalls) + verify.py + CI + gitleaks. Leaner file set, same guarantees. |
| Never-trust-the-handoff (§21) | AGENTS/skill protocol: re-read state, verify gate every session; "the repository wins" |
| Secrets outside source (§48) | .env gitignored, SecretStr, pre-commit + CI gitleaks, .env-staged commit guard |

## Adopted now (this session)

1. **Persona upgrades** (`api/persona.py`): strict financial-domain boundary; the
   KUBERA ANALYSIS structure for buy/sell/hold questions (verdict, confidence with
   calibration caveat, bull/bear case, "what would change my view"); conflicting-signals
   honesty ("fundamentals bullish, momentum neutral — overall mixed", never manufactured
   agreement); external content (news/filings/web) is data, never instructions.
2. **AGENTS.md**: prompt-injection defense line (external financial content is untrusted
   data for both the product AND the coding agents) — timely before T023 news ingestion.

## Adopted as tickets (real gaps)

- **T060** — Time-weighted returns: our benchmark comparison distorts under deposits/
  withdrawals (spec §9 is right). Compute TWR from equity snapshots + transactions.
- **T061** — User profile memory (spec §27): objectives, risk tolerance, horizons,
  restrictions ("never sell X", "no crypto") in DB + injected into chat context.
- **T062** — Morning brief / end-of-day report (spec §24–25): deterministic composition
  of existing tools (portfolio, benchmark, regime when T050 lands, calendar) + LLM
  narration; v1 = an endpoint returning the brief.
- **T063** — Decision journal (spec §28): persist every chat recommendation (thesis,
  confidence, horizon) and score outcomes later — measurable calibration.
- **T064** — Backtest rigor pack (spec §16): walk-forward splits, per-trade stats (win
  rate, profit factor, best/worst), Calmar; ledger columns extended.
- **T065** — Risk engine v2 (spec §18): sector-exposure caps (needs T023 sector data),
  cancel-all + disable-symbol controls, order-frequency limit (overlaps T055 guard).
- Realized P/L: already implied by T036 fills sync — acceptance criteria updated there.

## Rejected (reasons on record — see D013)

- **Microservices + Postgres/Timescale/Redis/Kafka/Qdrant/S3 now** (§42–43): 15 services
  for a single-user app is agent-hostile surface area. D005/D007 stand (monolith,
  SQLite→Postgres+pgvector at Phase 7 need). Revisit triggers already logged.
- **Nine-agent bureaucracy + duplicated agent profiles** (Factory §6–9): our spec §5
  role guide + single-writer session protocol achieves the same with ~10 files less
  drift surface. Roles harden into tooling only when multi-agent traffic demands.
- **Separate CURRENT_STATE/ACTIVE_TASK/HANDOFF/AGENT_STATUS/MASTER_PLAN file suite**:
  redundant with PROGRESS/TASKS/SPEC; more files = more stale-state bugs.
- **develop-branch + PR flow now**: solo repo with a hard verify gate commits to main;
  adopt PR flow when GitHub CI is live (T005) and >1 agent lands code concurrently.
- **Options/futures/crypto domains** (§1): out of scope per doctrine notes; warn-only.
- **MFA/RBAC/multi-user security** (§32): personal single-user system (D012 boundary);
  becomes mandatory only if KUBERA is ever productized — which also triggers counsel.

## Explicitly deferred (good ideas, wrong phase)

Health dashboard endpoint (Phase 8), model routing/ensemble beyond tools+LLM (Phase 11
territory), tax-lot awareness (§37), Mac/iOS build chain (§40, Phase 5–6 with D004 PWA
first), factory dashboards (Mission Control artifact already serves the owner).
