# Event-intelligence batch ("sell the news") — 2026-08-13 (binding: D019)

*Source: owner's fourth suggestion batch (event-driven architecture + NLP strategy).
Dispositions binding. IMPORTANT HYGIENE NOTE: the batch proposed ticket IDs
T075/T076/T077 for new ideas — those IDs already mean multi-timeframe confluence,
the event-risk guard, and the SHIPPED expected-move engine. The authoring AI did not
read TASKS.md. IDs below are the real ones. Owner: paste the AGENTS.md resume prompt
into any AI you use for ideation so proposals land against actual repo state.*

## The verdict in one line
The rumor / news / pricing decomposition is correct and ~70% already exists or is
ticketed; the genuinely new, honest, buildable piece is EVENT REACTION BASE RATES
(T083); the ML/NLP superstructure is Phase 7 material behind existing gates; the
99.9% framing stays rejected (D017 — no new evidence, not relitigated).

## Mapping the three elements to real tickets
- **The Expectation (rumor):** pre-event runup = trailing return into a known date —
  trivial once dates exist; consensus estimates = T023 (FMP evaluation, D017-enriched).
- **The Event (news):** earnings calendar + actuals + surprise history = T023;
  FOMC/CPI calendar = T076 (event-risk guard — the batch's "T026" is this).
- **The Pricing (context):** expected-move bands + vol-regime conditioning = T077,
  SHIPPED; regime/RVOL context = T050/T052, shipped. Options IV context stays in the
  recorded options-future note (doctrine caveat) — not built ad hoc.

## Adopted
- **NEW T083 — Event reaction base rates** (dep: T023 dates): for each historical
  earnings date, compute from OUR daily bars the event-day and next-day moves, split
  by beat/miss, plus pre-event runup into each; surface in briefings as base rates —
  "up 8% into the event; historically this name's beats still closed down 6 of 8
  times" answers 'should I hold through earnings' with EVIDENCE, not prophecy.
  Deterministic, hand-testable, zero new dependencies beyond T023's dates.
- **T076 enriched — sell-the-news caution flag:** runup-into-event above threshold
  + high expected-move pricing ⇒ the guard's size-down/no-trade reasons gain
  "priced-for-perfection" language; briefings surface it.
- **T023 enriched — verification-first stays:** confirm the owner's FMP key tier
  actually includes earnings calendar, consensus, AND transcripts before designing
  around them (transcripts are commonly paid-tier). This was already T023's rule;
  the batch independently agrees.
- **NEW T084 — Transcripts & filings as CONTEXT (Phase 7 gate):** fetch earnings-call
  transcripts (if tier allows) and summarize via our EXISTING LLM layer as clearly
  labeled qualitative context in briefings — tone/guidance summaries are narration
  of a document, never a priced signal. The 10-K/10-Q year-over-year textual-change
  idea ("Lazy Prices", Cohen–Malloy–Nguyen) is real research — recorded as a Phase 7
  research-agent candidate via SEC EDGAR, through the §7.7 pipeline, human-gated.
  No FinBERT dependency now: our LLM providers summarize; classifiers come later if
  T063 calibration shows the summaries correlate with anything.

## Rejected / deferred, with reasons (do not silently relitigate)
- **"99.9% accuracy"** — rejected in D017; still rejected. Accuracy targets like this
  are not achievable in markets; the goal is positive expected value with enforced
  risk. Any KUBERA output implying it would violate persona CORE_RULES.
- **XGBoost EPS predictor now** — Phase 7, behind the §7.7 research pipeline AND the
  T064 walk-forward promotion gate, like every signal source. Additional honest
  blocker: free-tier fundamentals are not point-in-time (restatement/survivorship
  bias) — training on them teaches the model corrupted history. Revisit when a
  point-in-time source exists and the journal (T063) can score its calls.
- **"High-confidence SELL ahead of earnings" / "Verdict: Sell 50%. Confidence 85/100"**
  — the sample output violates the persona contract: KUBERA gives case-for/against,
  falsifiable risk levels, and capped confidence; it does not issue directives with
  invented precision. The WORKFLOW is fine; the output style is not, and the persona
  guard tests already prevent it.
- **Sentiment-before-price framing** — rejected in D017/D018; transcripts enter as
  labeled context (T084), never as "detect shifts before price reflects them".

## The honest "hold through earnings?" answer (all real tickets)
T023 dates+consensus → runup (trivial) + T083 base rates + T077 bands (shipped) +
T076 guard ⇒ "You're up 8% into tomorrow's print. This name's 5-day expected band is
±4.1%. Over the last 8 earnings, 6 gapped down the next day even on beats. The event
guard will pause new entries an hour before. What you do with that is your call —
here's the case both ways." That is the doctrine-compliant version of the batch's
workflow, buildable without any ML.
