"""Live integration test against the Alpaca Data API (free IEX feed).
Skips when keys are absent or the environment has no route (Cowork sandbox, see I002)."""

import httpx
import pytest

from data.market_data import MarketDataClient, MarketDataError
from settings import KuberaSettings

live_settings = KuberaSettings()  # reads real env/.env on purpose

pytestmark = pytest.mark.skipif(
    not live_settings.alpaca_configured,
    reason="Alpaca keys not configured (owner task T006)",
)


def test_live_spy_trade_and_bars():
    try:
        with MarketDataClient(settings=live_settings) as c:
            trade = c.get_latest_trade("SPY")
            bars = c.get_daily_bars("SPY", days=10)
    except MarketDataError as e:
        if "Network error" in str(e):
            pytest.skip(f"no network route to Alpaca data from this environment: {e}")
        raise
    except (httpx.HTTPError, ImportError) as e:  # pragma: no cover - defensive
        pytest.skip(f"no usable network transport from this environment: {e}")
    assert trade.symbol == "SPY"
    assert trade.price > 0
    assert trade.exchange_ts.tzinfo is not None
    assert len(bars.bars) >= 5  # ~10 calendar days ≈ 6-8 trading days
    assert all(b.close > 0 for b in bars.bars)
