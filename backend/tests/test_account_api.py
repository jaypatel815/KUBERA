"""Tests for /api/account — deterministic regardless of ambient .env, no network."""

import httpx
from fastapi.testclient import TestClient
from test_alpaca import ACCOUNT_JSON, paper_settings

from api.main import app, get_alpaca_client
from data.alpaca import AlpacaClient
from settings import KuberaSettings, get_settings

client = TestClient(app)


def test_account_503_when_unconfigured():
    unconfig = KuberaSettings(_env_file=None, alpaca_api_key_id=None, alpaca_api_secret_key=None)
    app.dependency_overrides[get_settings] = lambda: unconfig
    try:
        r = client.get("/api/account")
        assert r.status_code == 503
        assert "T006" in r.json()["detail"]  # actionable, points at the fix
    finally:
        app.dependency_overrides.clear()


def test_account_returns_timestamped_snapshot():
    def override():
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=ACCOUNT_JSON)

        c = AlpacaClient(settings=paper_settings(), transport=httpx.MockTransport(handler))
        try:
            yield c
        finally:
            c.close()

    app.dependency_overrides[get_alpaca_client] = override
    try:
        r = client.get("/api/account")
        assert r.status_code == 200
        body = r.json()
        assert body["equity"] == 100000.75
        assert body["source"] == "alpaca-paper"
        assert "asof" in body and body["asof"]  # timestamped, always
    finally:
        app.dependency_overrides.clear()
