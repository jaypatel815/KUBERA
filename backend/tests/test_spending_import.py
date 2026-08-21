"""T156 — CSV spending import: rule-mapped categories, idempotent re-import,
sign-convention honesty. Fixtures mimic real card-export shapes."""

from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from data.models import Base, SpendingEntry
from data.spending_import import (
    SpendingImportError,
    categorize,
    import_csv,
    load_rules,
    write_starter_rules,
)

FIXTURES = Path(__file__).parent / "fixtures" / "household"
RULES = {"kroger": "groceries", "shell": "gas", "costco": "groceries",
         "netflix": "subscriptions"}


@pytest.fixture()
def db():
    engine = create_engine("sqlite://",
                           connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()
    engine.dispose()


def test_chase_like_import_with_negate(db):
    """Charges-as-negatives export: --negate makes charges positive; the
    payment row (positive in the file -> negative after negate) is skipped;
    the broken date is counted, never guessed."""
    r = import_csv(db, FIXTURES / "chase_like.csv", RULES, negate=True)
    assert r.total_rows == 6
    assert r.imported == 4            # 2x shell + kroger + mystery
    assert r.credits_skipped == 1     # the payment
    assert len(r.unparsed) == 1 and "row 7" in r.unparsed[0]
    assert r.uncategorized == 1       # MYSTERY MERCHANT
    assert "MYSTERY MERCHANT LLC" in r.unmatched_descriptions
    rows = db.execute(select(SpendingEntry)).scalars().all()
    assert len(rows) == 4
    by_cat = {}
    for e in rows:
        by_cat[e.category] = by_cat.get(e.category, 0) + 1
    # BOTH identical Shell charges stored (ordinal separates real duplicates)
    assert by_cat == {"gas": 2, "groceries": 1, "uncategorized": 1}
    assert all(e.source == "csv" and e.import_key for e in rows)
    # dates arrive ISO regardless of the US format in the file
    assert sorted(e.date for e in rows)[0] == "2026-08-03"


def test_reimport_is_idempotent(db):
    import_csv(db, FIXTURES / "chase_like.csv", RULES, negate=True)
    r2 = import_csv(db, FIXTURES / "chase_like.csv", RULES, negate=True)
    assert r2.imported == 0
    assert r2.duplicates_skipped == 4
    assert r2.uncategorized == 0      # duplicates never re-counted
    assert len(db.execute(select(SpendingEntry)).scalars().all()) == 4


def test_positive_export_needs_no_negate_and_warns_never_flips(db):
    r = import_csv(db, FIXTURES / "simple_positive.csv", RULES)
    assert r.imported == 2 and not r.warnings
    # the same file with negate turns charges negative -> all skipped;
    # nothing is ever flipped back automatically
    db2_rows_before = len(db.execute(select(SpendingEntry)).scalars().all())
    r2 = import_csv(db, FIXTURES / "simple_positive.csv", RULES, negate=True)
    assert r2.imported == 0 and r2.credits_skipped == 2
    assert len(db.execute(select(SpendingEntry)).scalars().all()) == db2_rows_before


def test_mostly_negative_without_negate_warns_loudly(db):
    r = import_csv(db, FIXTURES / "chase_like.csv", RULES)  # no negate
    assert any("--negate" in w for w in r.warnings)
    # and the charges were treated as credits (skipped), not silently flipped
    assert r.imported == 1            # only the payment row is positive
    assert r.credits_skipped == 4


def test_categorize_longest_substring_wins():
    rules = {"shell": "gas", "shell oil": "fuel"}
    assert categorize("SHELL OIL 5771", rules) == "fuel"
    assert categorize("SHELL CAR WASH", rules) == "gas"
    assert categorize("UNKNOWN PLACE", rules) is None


def test_unidentifiable_columns_are_a_named_refusal(db, tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("Foo,Bar\n1,2\n", encoding="utf-8")
    with pytest.raises(SpendingImportError, match="cannot identify columns"):
        import_csv(db, bad, RULES)


def test_rules_file_tolerates_bom_and_refuses_non_object(tmp_path):
    p = tmp_path / "rules.json"
    p.write_bytes(b'\xef\xbb\xbf{"KROGER": "Groceries", "_comment": "x"}')
    rules = load_rules(p)
    assert rules == {"kroger": "groceries"}   # lowercased, _keys dropped
    p.write_text('["not", "a", "map"]', encoding="utf-8")
    with pytest.raises(SpendingImportError, match="JSON object"):
        load_rules(p)


def test_starter_rules_round_trip(tmp_path):
    p = tmp_path / "spending_rules.json"
    write_starter_rules(p)
    rules = load_rules(p)
    assert rules["netflix"] == "subscriptions"
    assert "_comment" not in rules
