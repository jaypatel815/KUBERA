"""T109 — pre-registered selection rule (D029).

The rule that judges a promotion must exist before the experiment, carry a
version, and be stamped onto the run that it judged. These tests pin all
three properties, plus the refusals.
"""

import json

import httpx
import pytest
from test_alpaca import paper_settings

from backtest.ledger import promote_template
from backtest.selection_rule import SelectionRuleMissing, load_selection_rule
from backtest.strategies import make_regime_router
from data.db import make_engine, make_session_factory
from data.market_data import MarketDataClient
from data.models import Base


@pytest.fixture
def db():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with make_session_factory(engine)() as session:
        yield session
    engine.dispose()


def test_the_committed_rule_file_loads_and_is_versioned():
    """Guard on the repository itself: the pre-registered standard exists,
    carries a version, and states the D029 semantics it was adopted for."""
    rule = load_selection_rule()
    assert rule.version == "v1"
    assert "Ties go to the incumbent" in rule.text
    assert "never a gate" in rule.text
    assert "One structural change per revision" in rule.text


def test_version_line_tolerates_annotation(tmp_path):
    p = tmp_path / "RULE.md"
    p.write_text("# rule\n\nVersion: v9 (2030-01-01)\n\ngates...\n", encoding="utf-8")
    assert load_selection_rule(p).version == "v9"


def test_missing_rule_refuses_with_instructions(tmp_path):
    with pytest.raises(SelectionRuleMissing) as exc:
        load_selection_rule(tmp_path / "absent.md")
    msg = str(exc.value)
    assert "refused" in msg
    assert "git" in msg           # the fix is restore, not improvise


def test_unversioned_rule_refuses(tmp_path):
    p = tmp_path / "RULE.md"
    p.write_text("# a rule with no version line\n", encoding="utf-8")
    with pytest.raises(SelectionRuleMissing, match="no 'Version:' line"):
        load_selection_rule(p)


def test_promotion_run_records_the_rule_version_that_judged_it(db):
    """The record must say which standard it was held to — standards evolve
    and results are never re-judged retroactively."""
    closes = [100.0 + i for i in range(80)]
    bars_json = {"symbol": "SPY", "next_page_token": None, "bars": [
        {"t": f"2026-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}T04:00:00Z",
         "o": c, "h": c + 0.5, "l": c - 0.5, "c": c, "v": 1}
        for i, c in enumerate(closes)
    ]}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=bars_json)

    with MarketDataClient(settings=paper_settings(),
                          transport=httpx.MockTransport(handler)) as m:
        router = make_regime_router(lookback=40, momentum_lookback=60)
        _, row = promote_template(db, m, router, "regime_router", "SPY",
                                  rule_version="v1")
    assert json.loads(row.params_json)["selection_rule_version"] == "v1"

    # And without a version passed, nothing is fabricated.
    with MarketDataClient(settings=paper_settings(),
                          transport=httpx.MockTransport(handler)) as m:
        router = make_regime_router(lookback=40, momentum_lookback=60)
        _, row2 = promote_template(db, m, router, "regime_router", "QQQ")
    assert "selection_rule_version" not in json.loads(row2.params_json)
