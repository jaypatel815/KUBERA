"""Hand-computed tests for date alignment and comparison (analysis/benchmark.py)."""

import pytest

from analysis.benchmark import align_by_date, compare

PORT = [("2026-08-01", 100.0), ("2026-08-02", 110.0), ("2026-08-03", 99.0)]
BENCH = [("2026-08-02", 500.0), ("2026-08-03", 505.0), ("2026-08-04", 510.0)]


def test_align_inner_joins_on_date():
    dates, port, bench = align_by_date(PORT, BENCH)
    assert dates == ["2026-08-02", "2026-08-03"]
    assert port == [110.0, 99.0]
    assert bench == [500.0, 505.0]


def test_align_rejects_insufficient_overlap():
    with pytest.raises(ValueError) as exc:
        align_by_date([("2026-08-01", 100.0)], BENCH)
    assert "overlapping" in str(exc.value)
    assert "sync" in str(exc.value)  # actionable: tells the user how history accumulates


def test_compare_hand_computed():
    c = compare(PORT, BENCH)
    # portfolio over common dates: 110 -> 99 = -10%; benchmark: 500 -> 505 = +1%
    assert c.portfolio.cumulative_return == pytest.approx(-0.10)
    assert c.benchmark.cumulative_return == pytest.approx(0.01)
    assert c.excess_return == pytest.approx(-0.11)
    assert c.portfolio_norm == pytest.approx([1.0, 99.0 / 110.0])
    assert c.benchmark_norm == pytest.approx([1.0, 1.01])
    # 2 common dates -> 1 return -> vol/sharpe are None (too few points), drawdown valid
    assert c.portfolio.volatility_ann is None
    assert c.portfolio.sharpe_ann is None
    assert c.portfolio.max_drawdown_frac == pytest.approx(0.10)


def test_compare_longer_series_has_vol_and_sharpe():
    port = [("2026-08-0%d" % d, v) for d, v in [(1, 100.0), (2, 110.0), (3, 99.0), (4, 108.9)]]
    bench = [("2026-08-0%d" % d, v) for d, v in [(1, 50.0), (2, 51.0), (3, 50.5), (4, 52.0)]]
    c = compare(port, bench)
    assert c.portfolio.volatility_ann is not None
    assert c.benchmark.sharpe_ann is not None
    assert len(c.dates) == 4
