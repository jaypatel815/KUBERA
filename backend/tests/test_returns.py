import pytest

from analysis.returns import simple_return, total_pnl


def test_positive_return():
    assert simple_return(100.0, 110.0) == pytest.approx(0.10)


def test_negative_return():
    assert simple_return(200.0, 150.0) == pytest.approx(-0.25)


def test_flat_return():
    assert simple_return(50.0, 50.0) == 0.0


def test_total_pnl():
    assert total_pnl(1000.0, 1234.56) == pytest.approx(234.56)
    assert total_pnl(1000.0, 800.0) == pytest.approx(-200.0)


@pytest.mark.parametrize("bad_cost", [0.0, -10.0])
def test_bad_cost_basis_rejected(bad_cost):
    with pytest.raises(ValueError):
        simple_return(bad_cost, 100.0)
    with pytest.raises(ValueError):
        total_pnl(bad_cost, 100.0)
