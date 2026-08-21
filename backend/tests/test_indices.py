"""T157i — /api/indices: real levels through the named chain, never ETF
dollars. Pure-helper tests with fakes; the endpoint shape via TestClient."""

from types import SimpleNamespace

from api.main import compose_index_cards
from data.finnhub import FinnhubError


class FakeFinnhub:
    def __init__(self, ok=True):
        self.ok = ok

    def quote(self, symbol):
        if not self.ok:
            raise FinnhubError(f"Finnhub has no quote for '{symbol}' (c=0)")
        return {"price": 53277.01, "change": 517.80, "change_pct": 0.98,
                "prev_close": 52759.21}


class FakeFred:
    def latest(self, series_id):
        return SimpleNamespace(series_id=series_id, date="2026-08-20",
                               value=7674.37)


class FakeMarket:
    def get_daily_bars(self, sym, days=5):
        return SimpleNamespace(bars=[
            SimpleNamespace(close=100.0), SimpleNamespace(close=100.0)])

    def get_latest_trade(self, sym):
        return SimpleNamespace(price=100.43)


def test_finnhub_live_wins_the_chain():
    cards = compose_index_cards(FakeFinnhub(), FakeFred(), FakeMarket())
    dow = cards[0]
    assert dow["level"] == 53277.01
    assert dow["level_source"] == "finnhub-live"
    assert dow["change_abs"] == 517.80 and dow["change_pct"] == 0.98


def test_fred_close_is_the_dated_fallback_with_etf_percent():
    cards = compose_index_cards(FakeFinnhub(ok=False), FakeFred(), FakeMarket())
    sp = cards[1]
    assert sp["level"] == 7674.37
    assert sp["level_source"] == "fred-close 2026-08-20"
    # %% rides the tracking ETF, LABELED — and the implied points are derived
    # from the level, never from ETF dollars
    assert sp["change_pct"] == 0.43
    assert "ETF proxy" in sp["change_source"]
    assert abs(sp["change_abs"] - 7674.37 * 0.43 / 100.43) < 0.05


def test_no_provider_means_a_named_refusal_not_an_etf_price():
    cards = compose_index_cards(None, None, FakeMarket())
    for c in cards:
        assert c["level"] is None
        assert "NOT the index" in c["why"]
        # the %% line may still ride the ETF, labeled
        assert c["change_pct"] is not None


def test_endpoint_answers_without_keys():
    from fastapi.testclient import TestClient

    from api.main import app
    r = TestClient(app).get("/api/indices")
    assert r.status_code == 200
    d = r.json()
    assert [c["name"] for c in d["indices"]] == [
        "Dow Index", "S&P 500 Index", "NASDAQ Index"]
    assert "official FRED close" in d["note"]
