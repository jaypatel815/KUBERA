from datetime import datetime

from fastapi.testclient import TestClient

from api.main import VERSION, app

client = TestClient(app)


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["service"] == "kubera-api"
    assert body["version"] == VERSION
    # Every payload is timestamped and parseable — no undated data, ever.
    assert datetime.fromisoformat(body["time"]).tzinfo is not None
    # Reports config *state*, never values or secrets.
    assert isinstance(body["alpaca_configured"], bool)
    assert isinstance(body["paper_mode"], bool)
