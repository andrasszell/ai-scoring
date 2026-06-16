from pathlib import Path

from evidence_collection.collectors.product_docs import (
    ProductDocsCollector,
    build_product_docs_query,
    select_doc_results,
    url_on_company_domain,
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
    def __init__(self, payload=None, text=""):
        self._payload = payload
        self.text = text or (str(payload) if payload is not None else "")
        self.status_code = 200

    def json(self):
        return self._payload or {}


DOC_HTML = """
<html><body><p>Our product documentation describes how to build machine learning and
artificial intelligence applications with managed APIs for enterprise developers and
data scientists integrating generative AI into their solutions.</p></body></html>
"""


def _serp_settings(api_key="test-key", raw_dir="/tmp"):
    return type("S", (), {"serpapi_api_key": api_key, "raw_dir": raw_dir, "max_candidate_paragraphs": 40})()


def test_build_product_docs_query_requires_domain():
    assert build_product_docs_query(COMPANY) is not None
    assert build_product_docs_query({"ticker": "X"}) is None


def test_url_on_company_domain_accepts_subdomains():
    assert url_on_company_domain("https://learn.microsoft.com/azure/ai", "microsoft.com")


def test_select_doc_results_filters_external_links():
    organic = [
        {"link": "https://microsoft.com/docs/ai", "title": "AI docs"},
        {"link": "https://example.com/docs", "title": "External"},
    ]
    selected = select_doc_results(organic, "microsoft.com")
    assert len(selected) == 1
    assert "microsoft.com" in selected[0]["link"]


def test_product_docs_source_empty_without_domain(conn, monkeypatch):
    monkeypatch.setattr("evidence_collection.collectors.product_docs.settings", _serp_settings())
    ctx = CollectionContext(conn=conn, run_id=1, settings=settings)
    result = ProductDocsCollector().collect(ctx, {"ticker": "X", "company_name": "X Corp"})
    assert result.status == CollectionStatus.NO_RESULTS
    assert result.outcome_reason == OutcomeReason.SOURCE_EMPTY


def test_product_docs_filtered_to_zero_off_domain_results(conn, monkeypatch):
    monkeypatch.setattr("evidence_collection.collectors.product_docs.settings", _serp_settings())
    monkeypatch.setattr(
        "evidence_collection.collectors.product_docs.get",
        lambda url, **k: _FakeResponse(
            {"organic_results": [{"link": "https://example.com/docs", "title": "x"}]},
            text="{}",
        ),
    )
    ctx = CollectionContext(conn=conn, run_id=1, settings=settings)
    result = ProductDocsCollector().collect(ctx, COMPANY)
    assert result.status == CollectionStatus.NO_RESULTS
    assert result.outcome_reason == OutcomeReason.FILTERED_TO_ZERO


def test_product_docs_success_fetches_and_extracts(conn, monkeypatch, tmp_path):
    repo.upsert_companies(conn, [COMPANY])
    monkeypatch.setattr(
        "evidence_collection.collectors.product_docs.settings",
        _serp_settings(raw_dir=str(tmp_path)),
    )

    def fake_get(url, **kwargs):
        if "serpapi" in url:
            return _FakeResponse(
                {
                    "organic_results": [
                        {
                            "link": "https://learn.microsoft.com/azure/ai",
                            "title": "Azure AI documentation",
                            "date": "2024-01-01",
                        }
                    ]
                },
                text="{}",
            )
        return _FakeResponse(text=DOC_HTML)

    monkeypatch.setattr("evidence_collection.collectors.product_docs.get", fake_get)
    ctx = CollectionContext(conn=conn, run_id=1, settings=settings)
    result = ProductDocsCollector().collect(ctx, COMPANY)
    assert result.status == CollectionStatus.SUCCESS
    assert result.evidence_count >= 1
    assert result.documents_count == 1
    docs = conn.execute(
        "SELECT * FROM documents WHERE ticker='MSFT' AND source_type='product_documentation'"
    ).fetchall()
    assert len(docs) == 1


def test_reprocess_product_docs(conn, tmp_path):
    from evidence_collection.reprocess import reprocess_documents

    repo.upsert_companies(conn, [COMPANY])
    text_path = tmp_path / "doc.txt"
    text_path.write_text(
        "Our product documentation describes how to build machine learning and "
        "artificial intelligence applications with managed APIs for enterprise developers "
        "and data scientists integrating generative AI into their solutions.",
        encoding="utf-8",
    )
    repo.insert_document(
        conn,
        {
            "ticker": "MSFT",
            "source_type": "product_documentation",
            "source_url": "https://learn.microsoft.com/azure/ai",
            "source_date": "2024-01-01",
            "text_path": str(text_path),
            "content_hash": "prod-doc-1",
        },
    )
    totals = reprocess_documents(conn, sources=["product_docs"], tickers=["MSFT"])
    assert totals["documents"] == 1
    assert totals["evidence"] >= 1
