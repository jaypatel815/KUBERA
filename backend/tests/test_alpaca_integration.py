"""Live integration test against the Alpaca PAPER API (spec §9: integrations get real
sandbox tests, not just mocks). Skips cleanly when keys are absent (CI) or the
network is unavailable; runs for real on any machine with .env filled in (T006)."""

import httpx
import pytest

from data.alpaca import AlpacaClient, AlpacaError
from settings import KuberaSettings

live_settings = KuberaSettings()  # reads real env/.env on purpose

pytestmark = pytest.mark.skipif(
    not live_settings.alpaca_configured,
    reason="Alpaca paper keys not configured (owner task T006)",
)


def test_live_paper_account():
    try:
        with AlpacaClient(settings=live_settings) as c:
            acct = c.get_account()
    except AlpacaError as e:
        if "Network error" in str(e):
            pytest.skip(f"no network route to Alpaca from this environment: {e}")
        raise
    except (httpx.HTTPError, ImportError) as e:  # pragma: no cover - defensive
        # ImportError: e.g. proxy transport needing an extra package in a sandboxed env.
        pytest.skip(f"no usable network transport to Alpaca from this environment: {e}")
    assert acct.status in {"ACTIVE", "PAPER_ONLY", "ACCOUNT_UPDATED"}
    assert acct.currency == "USD"
    assert acct.equity >= 0
    assert acct.source == "alpaca-paper"
