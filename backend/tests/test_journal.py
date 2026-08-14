"""Decision journal (T063) — CRUD, marking, summary + v1 calibration hand-computed,
tool roundtrip, and the endpoint."""

from datetime import datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from test_alpaca import paper_settings

from api.main import app
from api.tools import ToolArgumentError, ToolContext, ToolError, registry
from data.journal import (
    list_decisions,
    mark_decision,
    record_decision,
    summarize_decisions,
)
from data.market_data import MarketDataClient
from data.models import Base

NOW = datetime(2026, 8, 13, 20, 0, 0, tzinfo=timezone.utc)


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
    engine.dispose()


def _record(db, **overrides):
    fields = dict(symbol="SPY", verdict="buy", confidence=0.6,
                  thesis="trend intact above the 20-bar average",
                  horizon_days=5, entry_price=100.0)
    fields.update(overrides)
    return record_decision(db, **fields)


def test_record_and_list(db):
    r = _record(db, regime="trending_up", regime_confidence=0.8, stop_price=95.0)
    assert r.id == 1 and r.followed is None
    rows = list_decisions(db)
    assert len(rows) == 1
    assert rows[0].regime == "trending_up" and rows[0].stop_price == pytest.approx(95.0)


def test_record_validation(db):
    with pytest.raises(ValueError, match="verdict"):
        _record(db, verdict="yolo")
    with pytest.raises(ValueError, match="confidence"):
        _record(db, confidence=1.5)


def test_mark_followed_and_override(db):
    r1, r2 = _record(db), _record(db, verdict="avoid")
    mark_decision(db, r1.id, True, "bought next open")
    mark_decision(db, r2.id, False, "bought it anyway")
    rows = {r.id: r for r in list_decisions(db)}
    assert rows[r1.id].followed is True
    assert rows[r2.id].followed is False and rows[r2.id].follow_note == "bought it anyway"
    with pytest.raises(ValueError, match="no journal entry"):
        mark_decision(db, 99, True)


def test_summary_and_calibration_hand(db):
    old = NOW - timedelta(days=10)  # past the 5-day horizon: evaluable
    young = NOW - timedelta(days=1)  # too young to judge
    _record(db, ts=old, verdict="buy", entry_price=100.0)     # latest 110 -> HIT
    _record(db, ts=old, verdict="avoid", entry_price=100.0)   # latest 110 -> MISS
    _record(db, ts=old, verdict="hold", entry_price=100.0)    # directionless: excluded
    _record(db, ts=young, verdict="buy", entry_price=100.0)   # unaged: excluded
    mark_decision(db, 1, True)
    mark_decision(db, 2, False)

    s = summarize_decisions(list_decisions(db), price_lookup=lambda sym: 110.0, now=NOW)
    assert s.total == 4
    assert s.by_verdict == {"buy": 2, "avoid": 1, "hold": 1}
    assert s.followed == 1 and s.overridden == 1 and s.unmarked == 2
    assert s.evaluated == 2 and s.hits == 1
    assert s.hit_rate == pytest.approx(0.5)
    assert "process check" in s.note


def test_summary_without_prices_skips_calibration(db):
    _record(db, ts=NOW - timedelta(days=10))
    s = summarize_decisions(list_decisions(db), price_lookup=None, now=NOW)
    assert s.evaluated == 0 and s.hit_rate is None
    assert s.avg_confidence == pytest.approx(0.6)


# --- tools + endpoint ---------------------------------------------------------

def test_record_and_journal_tools_roundtrip(db):
    out = registry.execute("record_decision", {
        "symbol": "aapl", "verdict": "trim", "confidence": 0.55,
        "thesis": "extended 12% above the 20-bar average into earnings",
        "horizon_days": 10, "entry_price": 230.0, "key_risk": "momentum persists",
        "regime": "trending_up", "regime_confidence": 0.8,
    }, ToolContext(db=db))
    assert out["recorded"] is True and out["decision"]["symbol"] == "AAPL"

    marked = registry.execute("mark_decision", {
        "decision_id": out["decision"]["id"], "followed": False,
        "note": "held through earnings anyway",
    }, ToolContext(db=db))
    assert marked["decision"]["followed"] is False

    j = registry.execute("get_journal", {}, ToolContext(db=db))  # no market: no calib
    assert j["summary"]["total"] == 1
    assert j["summary"]["overridden"] == 1
    assert j["summary"]["hit_rate"] is None
    assert j["decisions"][0]["key_risk"] == "momentum persists"


def test_lenient_args_accept_the_exact_failing_payloads(db):
    # I009: both payloads below are verbatim shapes from real failure logs.
    # Payload 1: the string "None" for absent optionals
    out = registry.execute("record_decision", {
        "symbol": "SPY", "verdict": "hold", "confidence": 0.6,
        "thesis": "trend intact; staying the course",
        "entry_price": 640.0, "target_price": "None", "regime_confidence": "None",
    }, ToolContext(db=db))
    assert out["recorded"] is True
    assert out["decision"]["target_price"] is None
    assert out["decision"]["regime_confidence"] is None

    # Payload 2: SHOUTED verdict + empty strings for absent optionals
    out2 = registry.execute("record_decision", {
        "symbol": "SPY", "verdict": "BUY", "confidence": 0.55,
        "thesis": "breakout held with volume confirmation",
        "entry_price": "", "target_price": "", "stop_price": "",
        "regime_confidence": "",
    }, ToolContext(db=db))
    assert out2["recorded"] is True
    assert out2["decision"]["verdict"] == "buy"
    assert out2["decision"]["entry_price"] is None

    # normalization never weakens REAL validation
    with pytest.raises(ToolArgumentError):
        registry.execute("record_decision", {
            "symbol": "SPY", "verdict": "YOLO", "confidence": 0.5,
            "thesis": "this should still be rejected properly",
        }, ToolContext(db=db))


def test_lenient_args_cover_triage_days_held(db):
    from api.tools import TriageArgs

    args = TriageArgs(symbol="SPY", entry_price="640.5", days_held="None")
    assert args.entry_price == pytest.approx(640.5)  # numeric strings still coerce
    assert args.days_held is None


def test_mark_unknown_id_is_tool_error(db):
    with pytest.raises(ToolError, match="no journal entry"):
        registry.execute("mark_decision", {"decision_id": 7, "followed": True},
                         ToolContext(db=db))


def test_journal_endpoint_with_calibration(db):
    from api import main as main_module

    _record(db, ts=NOW - timedelta(days=10), verdict="buy", entry_price=100.0)

    def handler(request: httpx.Request) -> httpx.Response:
        assert "/trades/latest" in request.url.path
        return httpx.Response(200, json={
            "symbol": "SPY",
            "trade": {"t": datetime.now(timezone.utc).isoformat(), "p": 110.0, "s": 1},
        })

    def fake_market():
        with MarketDataClient(settings=paper_settings(),
                              transport=httpx.MockTransport(handler)) as m:
            yield m

    app.dependency_overrides[main_module.get_market_client] = fake_market
    app.dependency_overrides[main_module.get_db_session] = lambda: db
    try:
        from fastapi.testclient import TestClient
        r = TestClient(app).get("/api/journal")
    finally:
        app.dependency_overrides.pop(main_module.get_market_client)
        app.dependency_overrides.pop(main_module.get_db_session)
    assert r.status_code == 200
    body = r.json()
    assert body["summary"]["evaluated"] == 1 and body["summary"]["hits"] == 1
    assert body["summary"]["hit_rate"] == pytest.approx(1.0)
