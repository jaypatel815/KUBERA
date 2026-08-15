"""Watchlist opportunity ranking (T068, D020/D021) — a pipeline, not a pile.

Cross-sectional scoring of candidate symbols so research arrives RANKED:

- relative strength (50%): 1/3/6-month returns, each expressed as a percentile
  RANK within the watchlist universe (D020's criterion; cross-sectional per
  D021's screener framing). Percentiles, not raw returns — a hot market
  shouldn't make everything look like a buy.
- regime fit (30%): the T050 classifier's label mapped to a fit score for
  long-side entries (trending_up 1.0, breakout_watch 0.6, range_bound 0.35,
  trending_down 0.0). A heuristic mapping, documented as such.
- payoff context (20%): 5-session forward moves over the window — win rate x
  payoff ratio, squashed to [0,1]. Description of the PAST, never a promise.

Deciles: with 10+ symbols the top/bottom 10% get flagged; below 10, just the
single best/worst. The short half of a cross-sectional momentum TEMPLATE stays
behind the D021 shorting decision — this ranking is research, not a strategy.
"""

from dataclasses import dataclass, field, replace

# trading-day windows for 1/3/6 months
RS_WINDOWS = (21, 63, 126)
W_RS, W_REGIME, W_PAYOFF = 0.5, 0.3, 0.2
REGIME_FIT = {"trending_up": 1.0, "breakout_watch": 0.6,
              "range_bound": 0.35, "trending_down": 0.0}
DEFAULT_FIT = 0.2  # unknown/unclassifiable


def window_return(closes: list[float], window: int) -> float | None:
    """Trailing `window`-bar simple return; None when history is too short."""
    if len(closes) < window + 1:
        return None
    if closes[-(window + 1)] <= 0:
        raise ValueError("closes must be positive")
    return closes[-1] / closes[-(window + 1)] - 1.0


def percentile_ranks(values: dict[str, float | None]) -> dict[str, float | None]:
    """Rank each value within the group -> [0,1]; None stays None. Ties share
    the mean of their positions (deterministic)."""
    present = sorted((v, k) for k, v in values.items() if v is not None)
    n = len(present)
    if n == 0:
        return {k: None for k in values}
    if n == 1:
        return {k: (0.5 if v is not None else None) for k, v in values.items()}
    ranks: dict[str, float] = {}
    i = 0
    while i < n:
        j = i
        while j + 1 < n and present[j + 1][0] == present[i][0]:
            j += 1
        mean_pos = (i + j) / 2
        for _, k in present[i:j + 1]:
            ranks[k] = mean_pos / (n - 1)
        i = j + 1
    return {k: (ranks[k] if v is not None else None) for k, v in values.items()}


def payoff_context(closes: list[float], horizon: int = 5) -> dict | None:
    """5-session forward-move stats over the window: win rate, payoff ratio,
    and a [0,1] score = clamp(win_rate * payoff_ratio / 2). None if <40 bars."""
    if len(closes) < 40:
        return None
    moves = [closes[i + horizon] / closes[i] - 1.0
             for i in range(len(closes) - horizon)]
    ups = [m for m in moves if m > 0]
    downs = [-m for m in moves if m < 0]
    win_rate = len(ups) / len(moves) if moves else 0.0
    avg_up = sum(ups) / len(ups) if ups else 0.0
    avg_down = sum(downs) / len(downs) if downs else 0.0
    payoff = (avg_up / avg_down) if avg_down > 0 else (2.0 if avg_up > 0 else 0.0)
    return {"win_rate": round(win_rate, 4), "payoff_ratio": round(payoff, 4),
            "score": round(min(1.0, win_rate * payoff / 2.0), 4)}


@dataclass(frozen=True)
class RankedSymbol:
    symbol: str
    score: float | None       # None = not enough history to rank honestly
    rs_percentile: float | None
    window_returns: dict      # "21"/"63"/"126" -> return | None
    regime_label: str
    regime_fit: float
    payoff: dict | None
    flags: list = field(default_factory=list)
    note: str | None = None


def rank_watchlist(closes_by_symbol: dict[str, list[float]],
                   regime_labels: dict[str, str]) -> list[RankedSymbol]:
    """The composer. Symbols lacking even the shortest RS window are listed
    unranked (score None) rather than silently dropped or guessed."""
    symbols = sorted(closes_by_symbol)
    if not symbols:
        return []
    per_window: dict[int, dict[str, float | None]] = {}
    for w in RS_WINDOWS:
        per_window[w] = percentile_ranks(
            {s: window_return(closes_by_symbol[s], w) for s in symbols})
    out = []
    for s in symbols:
        pcts = [per_window[w][s] for w in RS_WINDOWS if per_window[w][s] is not None]
        rs = sum(pcts) / len(pcts) if pcts else None
        label = regime_labels.get(s, "unknown")
        fit = REGIME_FIT.get(label, DEFAULT_FIT)
        pay = payoff_context(closes_by_symbol[s])
        if rs is None:
            out.append(RankedSymbol(
                symbol=s, score=None, rs_percentile=None,
                window_returns={str(w): window_return(closes_by_symbol[s], w)
                                for w in RS_WINDOWS},
                regime_label=label, regime_fit=fit, payoff=pay,
                note="not enough history to rank — listed, not scored",
            ))
            continue
        pay_score = pay["score"] if pay else 0.0
        score = W_RS * rs + W_REGIME * fit + W_PAYOFF * pay_score
        out.append(RankedSymbol(
            symbol=s, score=round(score, 4), rs_percentile=round(rs, 4),
            window_returns={str(w): (round(r, 4) if (r := window_return(
                closes_by_symbol[s], w)) is not None else None)
                for w in RS_WINDOWS},
            regime_label=label, regime_fit=fit, payoff=pay,
        ))
    ranked = sorted([r for r in out if r.score is not None],
                    key=lambda r: (-r.score, r.symbol))
    unranked = [r for r in out if r.score is None]
    n = len(ranked)
    if n:
        k = max(1, n // 10)
        flagged = []
        for i, r in enumerate(ranked):
            flags = []
            if i < k:
                flags.append("top_decile" if n >= 10 else "top")
            if i >= n - k:
                flags.append("bottom_decile" if n >= 10 else "bottom")
            flagged.append(replace(r, flags=flags))
        ranked = flagged
    return ranked + unranked
