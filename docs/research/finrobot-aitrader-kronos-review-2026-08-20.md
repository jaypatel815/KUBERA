# FinRobot / AI-Trader / Kronos — review & adoption (owner request, 2026-08-20)

Second owner-requested repo review (method as D036: fetch, read, map
against what KUBERA ships, adopt methodology never content). These three
are RESEARCH/ML repos — much closer to KUBERA's danger zones than the
Anthropic FSI checklists, so the doctrine gates (D017 no per-trade
probabilities, D029 research preconditions, D030 probe-first, D035
odds-not-predictions) do most of the judging.

Reviewed: AI4Finance-Foundation/FinRobot (Apache-2.0, 7.8k stars) ·
HKUDS/AI-Trader (license UNRESOLVED — MIT badge but the LICENSE file 404s;
paper arXiv:2512.10971 cited freely, code untouched) ·
shiyu-coder/Kronos (MIT code AND weights, 37.5k stars, AAAI 2026).

## The headline finding: AI-Trader's numbers are EVIDENCE FOR KUBERA'S DOCTRINE

The AI-Trader paper ran six frontier LLMs (GPT-5, Claude-3.7-Sonnet,
DeepSeek-v3.1, Qwen3-Max, Gemini-2.5-Flash, MiniMax-M2) as autonomous
traders in a live, data-uncontaminated benchmark, Oct-Nov 2025. Results:
in US equities 4 of 6 failed to beat QQQ buy-and-hold (GPT-5 1.56% vs
QQQ 1.87%; Gemini NEGATIVE); in A-shares ALL SIX lost to the index; in
crypto every agent lost money. Five weeks, small sample, said plainly —
but it is the best public measurement yet of the exact architecture
KUBERA REFUSES: an LLM making the trading decisions. KUBERA's split
(deterministic tested code decides and sizes; the LLM narrates; nothing
trades without the T064 promotion gate) is the design their data argues
for. RECORDED as supporting evidence on D017/D035 — the strongest
adoption from this batch is a fact, not a feature.

Their evaluation METHODOLOGY (live, time-consistent, information-isolated,
CR/Sortino/MDD vs a passive baseline) maps 1:1 onto what KUBERA already
does: paper loop vs SPY, Sortino/MDD in metrics (D020), and D029 custody
for contamination. Already-have; no new ticket.

## FinRobot — one probe seeded, one validation, the rest already-have

Their own tagline — "Numbers are code-calculated. Narratives are
LLM-assisted. Every output is provenance-tracked" — is KUBERA's founding
doctrine arrived at independently. Validation, not adoption.

- Bull/Bear/Judge debate agents → ALREADY HAVE, cheaper: the persona's
  ANALYSIS_STRUCTURE requires case-for/case-against in one pass; three
  extra LLM calls per question buy theater, not determinism. Rejected.
- Their pipelines (DCF/LBO/comps/IC memo) → same verdict as the Anthropic
  FSI review: banker work product, out of scope.
- DATA SOURCES: yfinance → REJECTED (unofficial API, ToS-gray, breaks
  without notice — KUBERA uses official APIs only). SEC EDGAR → already
  ours, deeper. **Finnhub → the one real lead**: an OFFICIAL API with a
  free tier that plausibly answers company news, basic sentiment, and
  earnings-surprise history — surfaces KUBERA's Alpaca news does not
  cover. D030/D034: probe before believing. **ADOPTED as T121**:
  scripts/finnhub_check.py built this session (statuses only, key from
  .env FINNHUB_API_KEY, never echoed); the owner's paste decides whether
  a FinnhubClient ticket exists at all.

## Kronos — the real Phase 7 candidate, seeded with its trap named

Kronos is a genuine artifact: a decoder-only foundation model over
tokenized OHLCV K-lines, MIT weights on HuggingFace (mini 4.1M / small
24.7M / base 102.3M params), trained on "12 billion K-line records from
45 global exchanges", fine-tune + top-K backtest harness included.
1.3M downloads last month. This is exactly the CANDIDATE-SIGNAL class
Phase 7 was designed to evaluate — and exactly what D029's preconditions
(holdout custody, experiment budgets, isolation — ALL BUILT) exist to
keep honest.

**THE TRAP, named before anyone falls in it**: Kronos trained on global
K-lines through its data cutoff. A zero-shot "backtest" of Kronos on
historical SPY is therefore a test ON ITS OWN TRAINING DATA — in-sample
performance wearing an out-of-sample costume. Any Kronos experiment that
reports a historical backtest as evidence is void. The pre-registered
protocol in the T122 seed REQUIRES: evaluation on post-training-cutoff
data only (paper-forward, or a custody-frozen post-cutoff holdout),
budgets opened BEFORE the first run, agent glue code inside the T110b
boundary, and the T064 promotion gate + selection rule before the paper
loop ever sees a Kronos-derived signal. CPU note: base at 102M/F32 is
~400MB — daily-bar inference needs no GPU, so the experiment is
feasible on the owner's machine.

DOCTRINE CHECK, honestly: Kronos FORECASTS prices; D035 refuses point
predictions AS ANSWERS TO THE OWNER. These are compatible: a forecast
consumed INSIDE a strategy that must earn promotion is a signal like any
other; the owner still hears odds and ranges, never "Kronos says 770".
The ticket states this so nobody re-litigates it.

- Fine-tuning Kronos on the owner's own trades/history → REJECTED
  (an overfit machine pointed at 131 fills; their own README calls the
  harness a non-production demo).
- Joining AI-Trader's live arena (ai4trade.ai registration) → REJECTED
  (ships prompts/positions to a third party; nothing for KUBERA there).

## Disposition summary

ADOPTED-BUILT: T121 probe (scripts/finnhub_check.py — owner runs, pastes).
ADOPTED-SEEDED: T122 Kronos candidate experiment (Phase 7-gated,
pre-registered protocol with the contamination rule verbatim).
RECORDED AS EVIDENCE: AI-Trader's published results, attached to D017/D035.
ALREADY-HAVE: arena-style metrics vs baseline; debate-in-one-pass;
provenance discipline; EDGAR.
REJECTED: yfinance (unofficial), LLM-as-trader architecture (their own
data), fine-tune-on-owner (overfit), arena registration (data egress),
AI-Trader code reuse (license unresolved — 404 LICENSE).

Sources: three repo pages + HF model cards + arXiv:2512.10971 and
arXiv:2508.02739, read 2026-08-20 via subagent extraction; licenses as
stated per repo above.
