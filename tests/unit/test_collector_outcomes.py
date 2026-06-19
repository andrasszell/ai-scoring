from evidence_collection.collectors.earnings import EarningsCallCollector
from evidence_collection.collectors.patents import PatentsCollector
from evidence_collection.collectors.research import ResearchCollector
from evidence_collection.collectors.sec_filings import SecFilingsCollector
from evidence_collection.collectors.serpapi import HiringCollector, ProductServiceCollector
from evidence_collection.config import settings
from evidence_collection.db import repository as repo
from evidence_collection.models import CollectionContext
from evidence_collection.outcomes import OutcomeReason
from evidence_collection.status import CollectionStatus

COMPANY = {"ticker": "MSFT", "company_name": "Microsoft Corporation", "company_id": "MSFT"}
SEC_COMPANY = {**COMPANY, "cik": "0000789019"}

SUBMISSIONS_10K = {
    "filings": {
        "recent": {
            "form": ["10-K"],
            "accessionNumber": ["0000789019-24-000001"],
            "primaryDocument": ["a10k.htm"],
            "filingDate": ["2024-06-30"],
        }
    }
}

SUBMISSIONS_NO_ANNUAL = {
    "filings": {
        "recent": {
            "form": ["10-Q"],
            "accessionNumber": ["0000789019-24-000002"],
            "primaryDocument": ["a10q.htm"],
            "filingDate": ["2024-03-31"],
        }
    }
}

NO_AI_HTML = (
    "<html><body><p>Ordinary quarterly results and inventory discussion only. "
    "No technology investments described herein.</p></body></html>"
)

AI_HTML = (
    "<html><body><p>We invest in artificial intelligence and machine learning "
    "across our product portfolio for enterprise customers.</p></body></html>"
)

class _FakeResponse:
    def __init__(self, payload, text=""):
        self._payload = payload
        self.text = text or str(payload)
        self.status_code = 200

    def json(self):
        return self._payload


def _serp_settings(api_key="test-key"):
    return type("S", (), {"serpapi_api_key": api_key})()


def _research_settings(api_key=""):
    return type("S", (), {"semantic_scholar_api_key": api_key})()


def test_products_source_empty(conn, monkeypatch):
    monkeypatch.setattr("evidence_collection.collectors.serpapi.settings", _serp_settings())
    monkeypatch.setattr(
        "evidence_collection.collectors.serpapi.get",
        lambda *a, **k: _FakeResponse({"organic_results": []}),
    )
    ctx = CollectionContext(conn=conn, run_id=1, settings=settings)
    result = ProductServiceCollector().collect(ctx, COMPANY)
    assert result.status == CollectionStatus.NO_RESULTS
    assert result.outcome_reason == OutcomeReason.SOURCE_EMPTY


def test_products_filtered_to_zero(conn, monkeypatch):
    monkeypatch.setattr("evidence_collection.collectors.serpapi.settings", _serp_settings())
    monkeypatch.setattr(
        "evidence_collection.collectors.serpapi.get",
        lambda *a, **k: _FakeResponse(
            {"organic_results": [{"title": "Office suite", "snippet": "productivity tools", "link": "https://x.com"}]}
        ),
    )
    ctx = CollectionContext(conn=conn, run_id=1, settings=settings)
    result = ProductServiceCollector().collect(ctx, COMPANY)
    assert result.status == CollectionStatus.NO_RESULTS
    assert result.outcome_reason == OutcomeReason.FILTERED_TO_ZERO
    assert result.source_hits == 1


def test_hiring_source_empty(conn, monkeypatch):
    monkeypatch.setattr("evidence_collection.collectors.serpapi.settings", _serp_settings())
    monkeypatch.setattr(
        "evidence_collection.collectors.serpapi.get",
        lambda *a, **k: _FakeResponse({"jobs_results": []}),
    )
    ctx = CollectionContext(conn=conn, run_id=1, settings=settings)
    result = HiringCollector().collect(ctx, COMPANY)
    assert result.status == CollectionStatus.NO_RESULTS
    assert result.outcome_reason == OutcomeReason.SOURCE_EMPTY


def test_research_source_empty(conn, monkeypatch):
    monkeypatch.setattr("evidence_collection.collectors.research.settings", _research_settings())
    monkeypatch.setattr(
        "evidence_collection.collectors.research.get",
        lambda *a, **k: _FakeResponse({"data": []}, text='{"data":[]}'),
    )
    ctx = CollectionContext(conn=conn, run_id=1, settings=settings)
    result = ResearchCollector().collect(ctx, COMPANY)
    assert result.status == CollectionStatus.NO_RESULTS
    assert result.outcome_reason == OutcomeReason.SOURCE_EMPTY


def test_research_filtered_to_zero(conn, monkeypatch):
    monkeypatch.setattr("evidence_collection.collectors.research.settings", _research_settings())
    monkeypatch.setattr(
        "evidence_collection.collectors.research.get",
        lambda *a, **k: _FakeResponse({"data": [{"title": ""}]}, text='{"data":[{"title":""}]}'),
    )
    ctx = CollectionContext(conn=conn, run_id=1, settings=settings)
    result = ResearchCollector().collect(ctx, COMPANY)
    assert result.status == CollectionStatus.NO_RESULTS
    assert result.outcome_reason == OutcomeReason.FILTERED_TO_ZERO
    assert result.source_hits == 1


def test_patents_source_empty(conn, monkeypatch):
    repo.upsert_companies(conn, [COMPANY])
    monkeypatch.setattr(
        "evidence_collection.collectors.patents.settings",
        type("S", (), {"patentsview_api_key": "test-key"})(),
    )
    monkeypatch.setattr(
        "evidence_collection.collectors.patents.get",
        lambda *a, **k: _FakeResponse({"total_hits": 0, "patents": []}),
    )
    ctx = CollectionContext(conn=conn, run_id=1, settings=settings)
    result = PatentsCollector().collect(ctx, COMPANY)
    assert result.status == CollectionStatus.NO_RESULTS
    assert result.outcome_reason == OutcomeReason.SOURCE_EMPTY


def test_patents_filtered_to_zero(conn, monkeypatch):
    repo.upsert_companies(conn, [COMPANY])
    monkeypatch.setattr(
        "evidence_collection.collectors.patents.settings",
        type("S", (), {"patentsview_api_key": "test-key"})(),
    )
    monkeypatch.setattr(
        "evidence_collection.collectors.patents.get",
        lambda *a, **k: _FakeResponse({"total_hits": 3, "patents": []}),
    )
    ctx = CollectionContext(conn=conn, run_id=1, settings=settings)
    result = PatentsCollector().collect(ctx, COMPANY)
    assert result.status == CollectionStatus.NO_RESULTS
    assert result.outcome_reason == OutcomeReason.FILTERED_TO_ZERO
    assert result.source_hits == 3


def test_research_rate_limited(conn, monkeypatch):
    import requests

    monkeypatch.setattr("evidence_collection.collectors.research.settings", _research_settings())

    def raise_429(*a, **k):
        response = type("R", (), {"status_code": 429, "text": "Too Many Requests"})()
        err = requests.HTTPError("429 Client Error")
        err.response = response
        raise err

    monkeypatch.setattr("evidence_collection.collectors.research.get", raise_429)
    ctx = CollectionContext(conn=conn, run_id=1, settings=settings)
    result = ResearchCollector().collect(ctx, COMPANY)
    assert result.status == CollectionStatus.RATE_LIMITED


def test_sec_source_empty_when_no_annual_filing(conn, monkeypatch, tmp_path):
    repo.upsert_companies(conn, [SEC_COMPANY])
    monkeypatch.setattr(
        "evidence_collection.collectors.sec_filings.settings",
        type("S", (), {"raw_dir": str(tmp_path), "max_candidate_paragraphs": 40})(),
    )
    monkeypatch.setattr(
        "evidence_collection.collectors.sec_filings.get",
        lambda url, **k: _FakeResponse(SUBMISSIONS_NO_ANNUAL, text="{}"),
    )
    ctx = CollectionContext(conn=conn, run_id=1, settings=settings)
    result = SecFilingsCollector().collect(ctx, SEC_COMPANY)
    assert result.status == CollectionStatus.NO_RESULTS
    assert result.outcome_reason == OutcomeReason.SOURCE_EMPTY


def test_sec_filtered_to_zero_when_filing_has_no_ai_paragraphs(conn, monkeypatch, tmp_path):
    repo.upsert_companies(conn, [SEC_COMPANY])
    monkeypatch.setattr(
        "evidence_collection.collectors.sec_filings.settings",
        type("S", (), {"raw_dir": str(tmp_path), "max_candidate_paragraphs": 40})(),
    )

    def fake_get(url, **k):
        if "submissions" in url:
            return _FakeResponse(SUBMISSIONS_10K, text="{}")
        return _FakeResponse({}, text=NO_AI_HTML)

    monkeypatch.setattr("evidence_collection.collectors.sec_filings.get", fake_get)
    ctx = CollectionContext(conn=conn, run_id=1, settings=settings)
    result = SecFilingsCollector().collect(ctx, SEC_COMPANY)
    assert result.status == CollectionStatus.NO_RESULTS
    assert result.outcome_reason == OutcomeReason.FILTERED_TO_ZERO
    assert result.documents_count == 1
    assert result.source_hits == 1


def test_sec_success_with_ai_paragraphs(conn, monkeypatch, tmp_path):
    repo.upsert_companies(conn, [SEC_COMPANY])
    monkeypatch.setattr(
        "evidence_collection.collectors.sec_filings.settings",
        type("S", (), {"raw_dir": str(tmp_path), "max_candidate_paragraphs": 40})(),
    )

    def fake_get(url, **k):
        if "submissions" in url:
            return _FakeResponse(SUBMISSIONS_10K, text="{}")
        return _FakeResponse({}, text=AI_HTML)

    monkeypatch.setattr("evidence_collection.collectors.sec_filings.get", fake_get)
    ctx = CollectionContext(conn=conn, run_id=1, settings=settings)
    result = SecFilingsCollector().collect(ctx, SEC_COMPANY)
    assert result.status == CollectionStatus.SUCCESS
    assert result.evidence_count >= 1
    assert result.source_hits == 1


def test_earnings_filtered_to_zero_when_transcript_has_no_ai_keywords(conn, monkeypatch, tmp_path):
    from datetime import date

    repo.upsert_companies(conn, [COMPANY])
    current_year = date.today().year
    plain = (
        "We discuss revenue growth and margin expansion across all business segments "
        "this quarter with strong cash flow generation."
    )
    monkeypatch.setattr(
        "evidence_collection.collectors.earnings.settings",
        type("S", (), {"fmp_api_key": "test-key", "raw_dir": str(tmp_path), "max_candidate_paragraphs": 40})(),
    )

    def fake_get(url, params=None):
        if params["year"] == current_year and params["quarter"] == 4:
            return _FakeResponse([{"date": "2025-10-25", "content": plain}])
        return _FakeResponse([])

    monkeypatch.setattr("evidence_collection.collectors.earnings.get_once", fake_get)
    ctx = CollectionContext(conn=conn, run_id=1, settings=settings)
    result = EarningsCallCollector().collect(ctx, COMPANY, limit_quarters=1)
    assert result.status == CollectionStatus.NO_RESULTS
    assert result.outcome_reason == OutcomeReason.FILTERED_TO_ZERO
    assert result.documents_count == 1
    assert result.source_hits == 1
