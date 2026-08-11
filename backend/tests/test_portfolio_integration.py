"""Live end-to-end: real paper account -> summarize. Skips without keys/network (I002)."""

import httpx
import pytest

from analysis.portfolio import summarize
from data.alpaca import AlpacaClient, AlpacaError
from settings import KuberaSettings

live_settings = KuberaSettings()  # reads real env/.env on purpose

pytestmark = pytest.mark.skipif(
    not live_settings.alpaca_configured,
    reason="Alpaca paper keys not configured (owner task T006)",
)


def test_live_portfolio_summary():
    try:
        with AlpacaClient(settings=live_settings) as c:
            acct = c.get_account()
            positions = c.get_positions()
    except AlpacaError as e:
        if "Network error" in str(e):
            pytest.skip(f"no network route to Alpaca from this environment: {e}")
        raise
    except (httpx.HTTPError, ImportError) as e:  # pragma: no cover - defensive
        pytest.skip(f"no usable network transport from this environment: {e}")
    s = summarize(positions)
    assert acct.equity >= 0
    assert s.total_market_value >= 0
    # a fresh paper account may hold nothing — both states are valid
    if s.positions:
        assert abs(sum(v.weight_frac for v in s.positions) - 1.0) < 1e-9
