"""Tests for GET /portfolio — deterministic, no network."""

import httpx
import pytest
from fastapi.testclient import TestClient
from test_alpaca import ACCOUNT_JSON, POSITIONS_JSON, paper_settings

from api.main import app, get_alpaca_client
from data.alpaca import AlpacaClient
from settings import KuberaSettings, get_settings

client = TestClient(app)


def override():
    def handler(request: httpx.Request) -> httpx.Response:
        if "/v2/account" in request.url.path:
            return httpx.Response(200, json=ACCOUNT_JSON)
        if "/v2/positions" in request.url.path:
            return httpx.Response(200, json=POSITIONS_JSON)
        return httpx.Response(404, json={})

    c = AlpacaClient(settings=paper_settings(), transport=httpx.MockTransport(handler))
    try:
        yield c
    finally:
        c.close()


def test_portfolio_live_computed_dated():
    app.dependency_overrides[get_alpaca_client] = override
    try:
        r = client.get("/portfolio")
        assert r.status_code == 200
        body = r.json()
        assert body["account"]["equity"] == 100000.75
        assert body["summary"]["total_market_value"] == pytest.approx(1651.00)
        assert body["summary"]["total_unrealized_pl"] == pytest.approx(148.50)
        assert body["summary"]["total_return_frac"] == pytest.approx(148.50 / 1502.50)
        assert body["positions"][0]["symbol"] == "AAPL"
        assert body["positions"][0]["weight_frac"] == pytest.approx(1.0)
        assert body["win_loss"]["winners"] == 1
        assert body["win_loss"]["best_symbol"] == "AAPL"
        assert body["asof"] and body["source"] == "alpaca-paper"
    finally:
        app.dependency_overrides.clear()


def test_portfolio_503_when_unconfigured():
    app.dependency_overrides[get_settings] = lambda: KuberaSettings(_env_file=None)
    try:
        r = client.get("/portfolio")
        assert r.status_code == 503
        assert "T006" in r.json()["detail"]
    finally:
        app.dependency_overrides.clear()
