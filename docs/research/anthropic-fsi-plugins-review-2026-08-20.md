# Anthropic FSI + plugin repos — review & adoption (owner request, 2026-08-20)

Reviewed at the owner's request: three Anthropic GitHub repos, dispositioned
against what KUBERA already ships. Method: fetched each repo's README and
structure, then read the two most KUBERA-relevant skills IN FULL
(wealth-management/tax-loss-harvesting, equity-research/earnings-preview).
All three repos are Apache-2.0; KUBERA adopts METHODOLOGY, written as our
own tested code — no text or code copied.

Repos: anthropics/financial-services (agents + FSI vertical skill bundles +
MCP connectors) · anthropics/claude-plugins-official (plugin directory +
packaging conventions) · anthropics/knowledge-work-plugins (role plugins
for Cowork).

## The big picture

These repos are ANALYST-WORKFLOW checklists — markdown skills that tell a
Claude session how to structure human-reviewed work product. KUBERA is a
different animal: the checklist steps that matter are implemented as
DETERMINISTIC, TESTED code (base rates, expected move, exit plans, risk
rails), and the persona narrates their outputs. So most of the value here
is not "install the skill" but "does their checklist name a step our
composition lacks?" Two did. The rest is already-have or out-of-doctrine.

## ADOPTED — built now

**T117 — Tax-loss harvesting scan (from wealth-management/tlh).** The one
genuinely missing personal-finance capability their checklist exposed.
KUBERA has everything the workflow needs and they don't: REAL recorded
fills (T016c), FIFO open lots with entry clocks (T091b), live prices.
Adopted as measurement-only: unrealized-loss candidates with ST/LT split
(the 365-day line), the wash-sale 30-day lookback flagged from the owner's
OWN recorded buys, and the 30-day forward no-rebuy date per candidate.
DELIBERATELY NOT adopted from their skill: replacement-security suggestions
(naming a specific buy is a recommendation — D017 posture stays), tax-rate
math (KUBERA doesn't know the owner's bracket; it reports the loss, not
the refund). Named limitations in every payload: single-account view (their
checklist is right that wash sales span ALL household accounts — KUBERA
sees Schwab-recorded fills only, and says so), DRIPs unknown, options lots
listed but unpriced on this feed. NOT TAX ADVICE, stated verbatim.

**T118 — Earnings preview composition (from equity-research/
earnings-preview).** Their step list: consensus, key metrics, bull/base/
bear scenarios, catalyst checklist, "search for the stock's earnings
reaction history", options-implied move. KUBERA MEASURES what they search
for: the reaction history is our T083 base-rate store with real SEC filing
clocks; the "implied move" analog is our T077 realized distribution
(labeled as such — it is NOT options-implied, and the payload says so);
the runup-into-the-print is T076b's priced-for-perfection input. Adopted
as one composition tool: next report date+timing, base rates, 1-day
expected-move distribution, 5-day runup, current position exposure.
DELIBERATELY NOT adopted: bull/base/bear price targets (point predictions
— D017/D035 refuse them; our scenario table IS the distribution),
consensus-estimate scraping (no honest free source measured; the FMP
paywalled tier has estimates — D034 upgrade-day item, noted).

## SEEDED — tickets, not built today

**T119 — Thesis view (from equity-research thesis-tracker/catalyst-
calendar).** The pieces exist distributed (watchlist note = thesis text,
exit plan = invalidation, events/earnings = catalysts, journal = history).
Seeded: one composition joining them per symbol. Not built now — the
distributed pieces answer today's questions; the unified view is UX.

**T120 — Package KUBERA as a plugin (from claude-plugins-official
conventions).** KUBERA's chat surface already reaches Claude Desktop via
the T045 MCP server + installer. The plugin format (.claude-plugin/
plugin.json + commands/) would make the same surface installable in Claude
Code/Cowork by URL. Seeded with a caveat: our MCP config is machine-local
(venv python path), so the manifest must template it — the repo's
install_mcp_config.py logic moves into the plugin's setup command.

## ALREADY HAVE — no action, recorded so nobody re-adopts

- equity-research morning-note → T062 briefs (ours is composed from
  deterministic sections, not drafted freehand).
- wealth-management client-review/portfolio-rebalance → weekly review +
  T093 risk contributions + sector exposure. Drift-vs-TARGET rebalancing
  needs owner-ratified target allocations — that is the T061 IPS's job;
  noted on T061, not a new ticket.
- financial-analysis comps/DCF/LBO/deck skills → out of scope by design:
  KUBERA advises the owner's trading, it does not draft banker work
  product. Nothing to adopt.
- fund-admin GL reconciliation discipline → KUBERA's cross-check culture
  already exceeds it for our domain (T016b three-bucket diff, statement
  reconciliation, 100%-win-rate-is-a-bug).
- knowledge-work-plugins (productivity, data, enterprise-search…) → for
  the OWNER'S Cowork sessions, not the KUBERA repo. Recommendation to the
  owner: installing `productivity` is worthwhile for general work; nothing
  KUBERA-side to build.
- managed-agent-cookbooks (headless deployment, subagent orchestration) →
  relevant the day KUBERA runs autonomously (D034 talks about that day);
  the deploy pattern is recorded here for Phase 8, not actionable now.

## REJECTED — with reasons

- Partner MCP connectors (Daloopa, FactSet, PitchBook, Morningstar, LSEG,
  S&P…): all subscription services. D034 stands — free tier until
  autonomy. Recorded as candidates for upgrade day alongside FMP paid.
- Replacement-security suggestions in TLH: a named buy recommendation
  from a checklist is exactly what D017 exists to refuse.
- Scenario price targets in earnings previews: the confidence trick again
  (D035). Our distribution IS the scenario framework, with honesty.
- Whisper numbers / consensus scraping: no measured free source; not
  built on vibes (D030).

Sources: the three repo READMEs + the two SKILL.md files, fetched
2026-08-20. Licenses: Apache-2.0 (methodology adopted, no content copied).
