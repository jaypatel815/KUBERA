# Review: "NousResearch/hermes-agent — The Self-Improving AI Agent" (Nous Research, 2026)

Reviewed 2026-08-18 by Gemini/Antigravity at the owner's request.
Source: https://github.com/NousResearch/hermes-agent

## Overview & Architecture

Hermes Agent is an open-source autonomous agent framework featuring a persistent learning loop. Unlike standard stateless LLM wrappers, Hermes is designed to self-improve across sessions through:
1. **Procedural Memory (Skills System)**: Autonomous synthesis and refinement of reusable skill templates (`agentskills.io` standard) based on successful task trajectories, with prompt optimization (e.g., DSPy/GEPA).
2. **Persistent Memory Stack**:
   - `MEMORY.md`: Technical knowledge, environment quirks, and system facts.
   - `USER.md`: User preferences, communication style, cognitive traits, and goals.
   - SQLite FTS5 / Honcho dialectic user modeling: Full-text and cognitive memory recall across sessions without overflowing context windows.
3. **Trajectory Compression**: Stateful summarization of lengthy tool call sequences and conversation trajectories (`/compress`).
4. **Headless Multi-Channel Gateway**: Accessible over terminal TUI, Web, Telegram, Discord, Slack, and Signal with MCP server support and cron automations.

---

## Comparison: Hermes Agent vs. KUBERA Architecture

| Hermes Agent Feature | KUBERA Architecture & Discipline | Verdict & Alignment |
|---|---|---|
| **Autonomous Skill Generation** | Tested deterministic code in `/backend/analysis` & `/backend/risk`; skill cheatsheets in `.agents/skills` | **Adopt for Research**: Enable Phase 7 Research Agent to package repeatable data ingestion and screening routines into standardized research skills. |
| **`MEMORY.md` (System Memory)** | `/project-memory/` (`PROGRESS.md`, `TASKS.md`, `DECISIONS.md`, `ISSUES.md`, `PROJECT_SPEC.md`) | **KUBERA is stronger**: Multi-agent shared memory contract with strict reciprocal review (D023), self-falsification (D028), and zero-fabrication rules. |
| **`USER.md` / Dialectic Modeling** | `IPS` (Investment Policy Statement), `analysis/autopsy.py` (behavioral metrics: revenge sizing, tilt tempo, 0DTE share) | **Adopt for Coaching**: Formalize persistent trader behavioral tendencies and psychological triggers for Phase 4 Chat & Phase 6 Coach (`T066`, `T087`). |
| **Trajectory Compression** | Token-efficient transcript logging; deterministic tool summaries | **Adopt for Chat**: Add structured payload compression for heavy tool outputs (multi-day tick data, backtest logs) to protect conversation context. |
| **Multi-Channel Gateway** | PWA Orb UI, FastAPI REST/SSE endpoints, Windows toast notifications (`run_checks.py`) | **Adopt for Alerts**: Lightweight webhook/bot bridge for critical risk alerts and morning briefing delivery when away from the terminal. |
| **Free-Form Math / LLM Logic** | **Strictly Forbidden** by AGENTS.md Priority Rule & Determinism Rule (money math only in tested Python code) | **Do Not Adopt**: Financial arithmetic, sizing, and risk limits must remain 100% deterministic and audited. |

---

## Key Takeaways & Actionable Recommendations for KUBERA

### 1. Dedicated Trader Psychological Profile (`USER.md` / Trader Persona)
- **Concept**: Hermes uses `USER.md` (and Honcho) to model user psychology, risk tolerance, and communication preferences separately from project code.
- **KUBERA Application (Phase 4 / Phase 6)**:
  - While the IPS defines formal financial mandates (max drawdowns, asset allocation), the conversation layer and real-time coach (`T066`, `T087`) need persistent visibility into the owner's observed psychological friction points (e.g., "tendency to over-trade after 2:00 PM", "prone to revenge sizing following 0DTE losses", "prefers concise, high-signal alerts over verbose narratives").
  - Can be surfaced deterministically alongside `get_ips` and `get_trading_autopsy` to tailor advice without guessing.

### 2. Standardized Research Skills for Phase 7 (`/backend/research_agent`)
- **Concept**: Hermes packages successful problem-solving workflows into declarative, reusable skills.
- **KUBERA Application**:
  - As Phase 7 introduces the autonomous research agent exploring market anomalies, SEC EDGAR filings, and alternative datasets, successful screening scripts and data transformation pipelines should be committed into a structured skill registry (`docs/research/skills/`).
  - This allows future research agents to invoke proven investigation patterns deterministically.

### 3. Tool Output Compression & Context Hygiene (`/compress`)
- **Concept**: Large tool outputs (e.g., hundreds of market bars or raw order executions) quickly saturate LLM context windows.
- **KUBERA Application**:
  - Ensure conversation endpoints and MCP tools provide compact, high-density summary views by default (with raw details available on demand), preventing context degradation during multi-turn portfolio reviews.

### 4. Out-of-Band Risk Alerts & Briefing Dispatcher
- **Concept**: Headless messaging gateway enables seamless delivery across platforms.
- **KUBERA Application**:
  - Augment local Windows toast notifications with an optional webhook/messaging adapter for morning briefings and real-time circuit-breaker alerts when away from the desktop.
