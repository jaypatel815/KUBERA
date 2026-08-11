from dataclasses import dataclass

import pytest

from analysis.portfolio import summarize


@dataclass
class P:
    symbol: str
    qty: float
    market_value: float
    cost_basis: float
    unrealized_pl: float


def test_two_position_aggregation():
    s = summarize([
        P("AAPL", 10, 1651.00, 1502.50, 148.50),
        P("SPY", 5, 2790.50, 2600.00, 190.50),
    ])
    assert s.total_market_value == pytest.approx(4441.50)
    assert s.total_cost_basis == pytest.approx(4102.50)
    assert s.total_unrealized_pl == pytest.approx(339.00)
    assert s.total_return_frac == pytest.approx(339.00 / 4102.50)
    # sorted by market value, weights sum to 1
    assert [v.symbol for v in s.positions] == ["SPY", "AAPL"]
    assert sum(v.weight_frac for v in s.positions) == pytest.approx(1.0)
    aapl = next(v for v in s.positions if v.symbol == "AAPL")
    assert aapl.return_frac == pytest.approx(148.50 / 1502.50)


def test_empty_portfolio():
    s = summarize([])
    assert s.total_market_value == 0
    assert s.total_return_frac is None
    assert s.positions == []


def test_zero_cost_basis_position_has_no_return_but_counts_in_totals():
    s = summarize([P("GIFT", 1, 100.0, 0.0, 100.0)])
    assert s.positions[0].return_frac is None
    assert s.total_market_value == pytest.approx(100.0)
    assert s.positions[0].weight_frac == pytest.approx(1.0)
