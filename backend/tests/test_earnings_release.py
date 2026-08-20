"""T084 — earnings-release text (ex99.1) as labeled context. Fixtures mirror
the owner's probe run (2026-08-19): accession 0000320193-26-000018, primary
aapl-20260730.htm, exhibit a8-kex991q3202606272026.htm 173,484 bytes."""

import httpx
import pytest

from api.tools import ToolContext, ToolError, registry
from data.edgar import EdgarClient, EdgarError, html_to_text
from settings import KuberaSettings

TICKER_MAP = {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}}

ACCESSION = "0000320193-26-000018"
FOLDER = "/Archives/edgar/data/320193/000032019326000018"

SUBMISSIONS = {
    "cik": 320193,
    "filings": {"recent": {
        "form":            ["8-K", "10-Q", "8-K"],
        "filingDate":      ["2026-07-30", "2026-07-31", "2026-01-29"],
        "items":           ["2.02,9.01", "", "2.02,9.01"],
        "accessionNumber": [ACCESSION, "0000320193-26-000019",
                            "0000320193-26-000002"],
        "primaryDocument": ["aapl-20260730.htm", "q.htm", "aapl-20260129.htm"],
        "acceptanceDateTime": ["2026-07-30T20:30:28.000Z", "", ""],
    }},
}

INDEX = {"directory": {"item": [
    {"name": "aapl-20260730.htm", "size": "38350"},
    {"name": "a8-kex991q3202606272026.htm", "size": "173484"},
    {"name": "small_ex99-2.htm", "size": "512"},        # smaller ex99: not picked
    {"name": "logo.jpg", "size": "9000"},
    {"name": "index.json", "size": "612"},
]}}

RELEASE_HTML = (
    "<html><head><title>skip</title><style>p{color:red}</style></head><body>"
    "<script>var tracker = 1;</script>"
    "<p>Apple reports third quarter results</p>"
    "<div>Revenue &amp; services margin expanded.</div>"
    "<table><tr><td>Net sales</td><td>$94,930</td></tr></table>"
    "</body></html>"
)


def _client(sub=SUBMISSIONS, index=INDEX, doc_html=RELEASE_HTML) -> EdgarClient:
    def handler(request: httpx.Request) -> httpx.Response:
        p = request.url.path
        if p.endswith("/files/company_tickers.json"):
            return httpx.Response(200, json=TICKER_MAP)
        if "/submissions/" in p:
            return httpx.Response(200, json=sub)
        if p == f"{FOLDER}/index.json":
            return httpx.Response(200, json=index)
        if p.startswith(FOLDER + "/"):
            return httpx.Response(200, text=doc_html)
        return httpx.Response(404, json={})

    return EdgarClient(
        settings=KuberaSettings(_env_file=None, edgar_contact="p@example.com"),
        transport=httpx.MockTransport(handler))


def _sub_variant(**recent_over) -> dict:
    recent = dict(SUBMISSIONS["filings"]["recent"])
    recent.update(recent_over)
    return {"cik": 320193, "filings": {"recent": recent}}


# ------------------------------------------------------------ html_to_text


def test_html_to_text_skips_script_style_and_flattens_blocks():
    text = html_to_text(RELEASE_HTML)
    lines = [ln for ln in text.splitlines() if ln]
    assert lines == ["Apple reports third quarter results",
                     "Revenue & services margin expanded.",   # entity decoded
                     "Net sales $94,930"]                     # cells flattened
    assert "tracker" not in text and "color:red" not in text and \
        "skip" not in text


# --------------------------------------------------------- earnings_release


def test_picks_newest_8k_and_largest_ex99():
    with _client() as c:
        rel = c.earnings_release("aapl")
    assert rel.accession == ACCESSION                  # newest 2.02, not Jan
    assert rel.filing_date.isoformat() == "2026-07-30"
    assert rel.doc_name == "a8-kex991q3202606272026.htm"   # largest ex99 wins
    assert rel.doc_kind == "ex99-exhibit"
    assert rel.acceptance_utc is not None and rel.acceptance_utc.hour == 20
    assert "Apple reports third quarter results" in rel.text
    assert rel.truncated is False
    assert rel.text_chars_total == len(rel.text)
    assert rel.source == "sec-edgar" and rel.asof


def test_truncation_is_visible_never_silent():
    with _client() as c:
        rel = c.earnings_release("AAPL", max_chars=10)
    assert rel.truncated is True and len(rel.text) == 10
    assert rel.text_chars_total > 10                   # the cap is on display


def test_no_ex99_falls_back_to_primary_by_name():
    idx = {"directory": {"item": [
        {"name": "aapl-20260730.htm", "size": "38350"},
        {"name": "logo.jpg", "size": "9000"},
    ]}}
    with _client(index=idx) as c:
        rel = c.earnings_release("AAPL")
    assert rel.doc_name == "aapl-20260730.htm"
    assert "no ex99" in rel.doc_kind                   # the fallback is NAMED


def test_refusals_are_named():
    # nothing readable at all
    with _client(index={"directory": {"item": [
            {"name": "logo.jpg", "size": "1"}]}}) as c:
        with pytest.raises(EdgarError, match="nothing safe to read"):
            c.earnings_release("AAPL")
    # no earnings 8-K in the window
    with _client(sub=_sub_variant(items=["5.02", "", "5.02"])) as c:
        with pytest.raises(EdgarError, match="no earnings 8-K"):
            c.earnings_release("AAPL")
    # accession missing -> shape refusal, never a guessed URL
    with _client(sub=_sub_variant(accessionNumber=["", "", ""])) as c:
        with pytest.raises(EdgarError, match="no accessionNumber"):
            c.earnings_release("AAPL")
    # index shape changed
    with _client(index={"directory": {"item": "surprise"}}) as c:
        with pytest.raises(EdgarError, match="shape changed"):
            c.earnings_release("AAPL")


# ------------------------------------------------------------------- tool


def test_tool_returns_labeled_context():
    with _client() as c:
        out = registry.execute("get_earnings_release", {"symbol": "aapl"},
                               ToolContext(edgar=c))
    assert out["accession"] == ACCESSION
    assert out["document_kind"] == "ex99-exhibit"
    assert out["acceptance_utc"].startswith("2026-07-30T20:30:28")
    assert "never a priced signal" in out["note"]
    assert "not" in out["note"] and "Q&A" in out["note"]   # scope honesty
    assert out["truncated"] is False and out["asof"]


def test_tool_without_edgar_names_the_fix():
    with pytest.raises(ToolError, match="EDGAR_CONTACT"):
        registry.execute("get_earnings_release", {"symbol": "AAPL"},
                         ToolContext())
