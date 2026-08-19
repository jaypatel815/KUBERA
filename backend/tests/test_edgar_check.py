"""T084a — summarize_index parse rule, importlib-by-path (T106 precedent).

The probe script itself needs sec.gov (owner's machine); the PURE parse
helper is what the filing-index step trusts, so THAT is pinned here against
the documented index.json shape — and against malformed variants, which must
raise (the probe turns raises into a named SHAPE? line, never a crash-with-
traceback in the middle of the owner's table).
"""

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "edgar_check.py"


def _mod():
    spec = importlib.util.spec_from_file_location("edgar_check_t084a", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


DOCUMENTED = {
    "directory": {
        "item": [
            {"name": "aapl-20260730.htm", "size": "24681"},
            {"name": "a8-kex991.htm", "size": "104321"},
            {"name": "ny20026310x2_ex99-1.htm", "size": ""},
            {"name": "logo.jpg", "size": "9000"},
            {"name": "index.json", "size": "612"},
        ],
        "name": "/Archives/edgar/data/320193/000032019326000077",
    }
}


def test_documented_shape_names_primary_and_exhibits():
    s = _mod().summarize_index(DOCUMENTED, "aapl-20260730.htm")
    assert s["count"] == 5
    assert s["primary"] == ("aapl-20260730.htm", 24681)
    names = [n for n, _ in s["exhibits"]]
    # both exhibit spellings collapse to ex99…; empty size parses to 0
    assert names == ["a8-kex991.htm", "ny20026310x2_ex99-1.htm"]
    assert dict(s["exhibits"])["ny20026310x2_ex99-1.htm"] == 0
    # logo.jpg and index.json are NOT exhibits
    assert "logo.jpg" not in names and "index.json" not in names


def test_exhibit_name_variants_collapse():
    mod = _mod()
    idx = {"directory": {"item": [
        {"name": "d12dex991.htm", "size": "1"},
        {"name": "EX-99_1.HTM", "size": "2"},
        {"name": "ex98.htm", "size": "3"},          # not 99
        {"name": "press99.htm", "size": "4"},        # no "ex" before 99
    ]}}
    names = [n for n, _ in mod.summarize_index(idx, "")["exhibits"]]
    assert names == ["d12dex991.htm", "EX-99_1.HTM"]


def test_missing_primary_and_empty_directory():
    mod = _mod()
    s = mod.summarize_index(DOCUMENTED, "not-there.htm")
    assert s["primary"] is None                      # UNLISTED, not a guess
    empty = mod.summarize_index({"directory": {"item": []}}, "x.htm")
    assert empty == {"count": 0, "primary": None, "exhibits": []}


def test_malformed_shapes_raise_for_the_shape_line():
    mod = _mod()
    with pytest.raises(ValueError, match="not an object"):
        mod.summarize_index(["not", "a", "dict"], "x")
    with pytest.raises(ValueError, match="not a list"):
        mod.summarize_index({"directory": {"item": "surprise"}}, "x")
    # junk rows are dropped, junk sizes become 0 — never a crash
    s = mod.summarize_index(
        {"directory": {"item": [{"size": "5"}, {"name": "a.htm",
                                                "size": "big"}]}}, "a.htm")
    assert s == {"count": 1, "primary": ("a.htm", 0), "exhibits": []}
