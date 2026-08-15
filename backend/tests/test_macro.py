"""Macro context (T080) — FRED client mechanics (missing-value skipping, errors,
key requirement) + composition conventions hand-checked + tool/endpoint."""

import httpx
import pytest
from fastapi.testclient import TestClient
from test_alpaca import paper_settings

from analysis.macro import compose_macro_context
from api.main import app
from api.tools import ToolContext, registry
from data.fred import SERIES, FredClient, FredError
from settings import ConfigError, KuberaSettings

client = TestClient(app)


def fred_settings() -> KuberaSettings:
    base = paper_settings()
    return base.model_copy(update={"fred_api_key": base.alpaca_api_secret_key})


def obs_json(rows):
    return {"observations": [{"date": d, "value": v} for d, v in rows]}


def make_fred(handler) -> FredClient:
    return FredClient(settings=fred_settings(), transport=httpx.MockTransport(handler))


# --- client -------------------------------------------------------------------

def test_latest_skips_missing_values():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["series_id"] == "VIXCLS"
        assert request.url.params["api_key"]  # key attached, value never asserted
        return httpx.Response(200, json=obs_json(
            [("2026-08-13", "."), ("2026-08-12", "."), ("2026-08-11", "17.4")]))

    with make_fred(handler) as f:
        o = f.latest("VIXCLS")
    assert o.value == pytest.approx(17.4)
    assert o.date == "2026-08-11"  # the observation's own date, not today
    assert o.asof.tzinfo is not None and o.source == "fred"


def test_fred_errors_are_actionable():
    with make_fred(lambda r: httpx.Response(400, json={})) as f, \
            pytest.raises(FredError, match="FRED_API_KEY"):
        f.latest("T10Y2Y")
    with make_fred(lambda r: httpx.Response(200, json=obs_json([("2026-08-13", ".")]))) as f, \
            pytest.raises(FredError, match="no usable"):
        f.latest("T10Y2Y")


def test_missing_key_fails_fast():
    s = paper_settings().model_copy(update={"fred_api_key": None})
    with pytest.raises(ConfigError, match="FRED_API_KEY"):
        FredClient(settings=s)


# --- composition conventions --------------------------------------------------

def test_macro_composition_calm():
    c = compose_macro_context(
        yield_curve=("2026-08-12", 0.55), vix=("2026-08-12", 13.2),
        real_rate=("2026-08-12", 1.4), fed_funds=("2026-08-12", 4.33),
    )
    labels = {r.name: r.label for r in c.reads}
    assert labels["yield_curve_10y2y"] == "normal"
    assert labels["vix"] == "calm"
    assert labels["real_rate_10y"] == "positive"
    assert c.caution_count == 0
    assert "never a trade signal" in c.note


def test_macro_composition_stormy():
    c = compose_macro_context(
        yield_curve=("2026-08-12", -0.35), vix=("2026-08-13", 31.0),
        real_rate=("2026-08-11", 2.4), fed_funds=("2026-08-12", 5.33),
    )
    labels = {r.name: r.label for r in c.reads}
    assert labels["yield_curve_10y2y"] == "inverted"
    assert labels["vix"] == "stressed"
    assert labels["real_rate_10y"] == "restrictive"
    assert c.caution_count == 3
    assert any("inverted" in s and "not a timer" in s for s in c.cautionary_signals)
    # each caution carries its series' own observation date
    assert any("2026-08-13" in s for s in c.cautionary_signals)


@pytest.mark.parametrize("vix, bucket", [(14.9, "calm"), (15.0, "normal"),
                                         (19.9, "normal"), (20.0, "elevated"),
                                         (29.9, "elevated"), (30.0, "stressed")])
def test_vix_bucket_boundaries(vix, bucket):
    c = compose_macro_context(("d", 1.0), ("d", vix), ("d", 1.0), ("d", 4.0))
    assert {r.name: r.label for r in c.reads}["vix"] == bucket


# --- tool + endpoint ----------------------------------------------------------

VALUES = {"T10Y2Y": "-0.10", "VIXCLS": "22.5", "DFII10": "1.9", "DFF": "4.33"}


def routing_handler(request: httpx.Request) -> httpx.Response:
    if "/fred/release/dates" in request.url.path:   # T076 calendar
        return httpx.Response(200, json={"release_dates": [
            {"date": "2099-01-15"}]})
    sid = request.url.params["series_id"]
    return httpx.Response(200, json=obs_json([("2026-08-12", VALUES[sid])]))


def test_get_macro_context_tool():
    with make_fred(routing_handler) as f:
        out = registry.execute("get_macro_context", {}, ToolContext(fred=f))
    m = out["macro"]
    assert {r["name"] for r in m["reads"]} == set(SERIES)
    assert m["caution_count"] == 2  # inverted curve + elevated VIX; real rate 1.9 ok
    assert "upcoming_releases" in m  # T076: calendar surfaced (2099 is out of horizon)
    assert m["upcoming_releases"] == []
    assert out["source"] == "fred" and out["asof"]


def test_macro_endpoint():
    from api import main as main_module

    def fake_fred():
        with make_fred(routing_handler) as f:
            yield f

    app.dependency_overrides[main_module.get_fred_client] = fake_fred
    try:
        r = client.get("/api/macro")
    finally:
        app.dependency_overrides.pop(main_module.get_fred_client)
    assert r.status_code == 200
    assert r.json()["macro"]["caution_count"] == 2
