from evidence_collection.collectors.press_releases import (
    PressReleasesCollector,
    build_press_query,
    parse_press_rows,
)
from evidence_collection.config import settings
from evidence_collection.db import repository as repo
from evidence_collection.models import CollectionContext
from evidence_collection.outcomes import OutcomeReason
from evidence_collection.status import CollectionStatus

COMPANY = {
    "ticker": "MSFT",
    "company_name": "Microsoft Corporation",
    "company_id": "MSFT",
    "website_domain": "microsoft.com",
}


class _FakeResponse:
    def __init__(self, payload, text=""):
        self._payload = payload
        self.text = text or str(payload)
        self.status_code = 200

    def json(self):
        return self._payload


def _serp_settings(api_key="test-key"):
    return type("S", (), {"serpapi_api_key": api_key})()


def test_build_press_query_uses_site_when_domain_known():
    query = build_press_query(COMPANY, conn=None)
    assert query.startswith("site:microsoft.com")
    assert "press release" in query.lower() or "press" in query.lower()


def test_build_press_query_falls_back_to_company_name():
    query = build_press_query(
        {"ticker": "X", "company_name": "Acme Corp"},
        conn=None,
    )
    assert '"Acme"' in query


def test_parse_press_rows_filters_non_ai_results():
    collector = PressReleasesCollector()
    rows = parse_press_rows(
        collector,
        COMPANY,
        "q",
        [{"title": "Quarterly results", "snippet": "Revenue up", "link": "https://microsoft.com/q"}],
    )
    assert rows == []


def test_parse_press_rows_keeps_ai_press_hits():
    collector = PressReleasesCollector()
    rows = parse_press_rows(
        collector,
        COMPANY,
        "q",
        [
            {
                "title": "Microsoft announces generative AI platform",
                "snippet": "Press release on new machine learning tools",
                "link": "https://www.prnewswire.com/news/microsoft-ai",
                "date": "Jan 5, 2024",
            }
        ],
    )
    assert len(rows) == 1
    assert rows[0]["source_type"] == "press_release"
    assert rows[0]["source_category"] == "press_release"
    assert rows[0]["source_reliability"] == "medium"


def test_press_source_empty(conn, monkeypatch):
    monkeypatch.setattr("evidence_collection.collectors.press_releases.settings", _serp_settings())
    monkeypatch.setattr(
        "evidence_collection.collectors.press_releases.get",
        lambda *a, **k: _FakeResponse({"organic_results": []}),
    )
    ctx = CollectionContext(conn=conn, run_id=1, settings=settings)
    result = PressReleasesCollector().collect(ctx, COMPANY)
    assert result.status == CollectionStatus.NO_RESULTS
    assert result.outcome_reason == OutcomeReason.SOURCE_EMPTY


def test_press_filtered_to_zero(conn, monkeypatch):
    monkeypatch.setattr("evidence_collection.collectors.press_releases.settings", _serp_settings())
    monkeypatch.setattr(
        "evidence_collection.collectors.press_releases.get",
        lambda *a, **k: _FakeResponse(
            {"organic_results": [{"title": "Dividend declared", "snippet": "cash", "link": "https://x.com"}]}
        ),
    )
    ctx = CollectionContext(conn=conn, run_id=1, settings=settings)
    result = PressReleasesCollector().collect(ctx, COMPANY)
    assert result.status == CollectionStatus.NO_RESULTS
    assert result.outcome_reason == OutcomeReason.FILTERED_TO_ZERO
    assert result.source_hits == 1


def test_press_success(conn, monkeypatch):
    repo.upsert_companies(conn, [COMPANY])
    monkeypatch.setattr("evidence_collection.collectors.press_releases.settings", _serp_settings())
    monkeypatch.setattr(
        "evidence_collection.collectors.press_releases.get",
        lambda *a, **k: _FakeResponse(
            {
                "organic_results": [
                    {
                        "title": "Microsoft press release on AI assistant",
                        "snippet": "artificial intelligence copilot announcement",
                        "link": "https://news.microsoft.com/press",
                    }
                ]
            }
        ),
    )
    ctx = CollectionContext(conn=conn, run_id=1, settings=settings)
    result = PressReleasesCollector().collect(ctx, COMPANY)
    assert result.status == CollectionStatus.SUCCESS
    assert result.evidence_count == 1
