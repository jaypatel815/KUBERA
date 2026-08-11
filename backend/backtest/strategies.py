"""Strategy templates on the T030 contract: closes-so-far -> target weight [0..1]."""

from typing import Sequence

from analysis.metrics import sma


def buy_and_hold(closes: Sequence[float]) -> float:
    """Fully invested from the first decision onward."""
    return 1.0


def make_sma_cross(fast: int = 50, slow: int = 200):
    """Long when SMA(fast) > SMA(slow); flat otherwise (and while history is too short)."""
    if not 1 <= fast < slow:
        raise ValueError(f"need 1 <= fast < slow, got fast={fast} slow={slow}")

    def sma_cross(closes: Sequence[float]) -> float:
        if len(closes) < slow:
            return 0.0
        return 1.0 if sma(closes, fast) > sma(closes, slow) else 0.0

    sma_cross.__name__ = f"sma_cross_{fast}_{slow}"
    return sma_cross
