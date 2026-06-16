import json

from evidence_collection.collectors.serpapi import HiringCollector, ProductServiceCollector, parse_job_rows, _job_source
from evidence_collection.config import settings
from evidence_collection.dates import DATE_PROVENANCE_ORIGIN, DATE_PROVENANCE_RETRIEVAL
from evidence_collection.models import CollectionContext
from evidence_collection.status import CollectionStatus

COMPANY = {"ticker": "MSFT", "company_name": "Microsoft Corporation"}

SAMPLE_JOBS = [
    {"title": "ML Engineer", "company_name": "Microsoft", "location": "Remote",
     "via": "via LinkedIn", "apply_options": [{"link": "https://linkedin.com/jobs/1"}]},
    {"title": "Data Scientist", "company_name": "Microsoft", "location": "Seattle",
     "via": "via Indeed", "share_link": "https://google.com/share/2"},
]


def test_parse_job_rows_counts_linkedin():
    rows, linkedin = parse_job_rows(HiringCollector(), COMPANY, "q", SAMPLE_JOBS)
    assert len(rows) == 2
    assert linkedin == 1


def test_parse_job_rows_sets_collector_version_and_source_type():
    rows, _ = parse_job_rows(HiringCollector(), COMPANY, "q", SAMPLE_JOBS)
    assert rows[0]["collector_name"] == "hiring_jobs"
    assert rows[0]["collector_version"] == "1.0.0"
    assert rows[0]["source_type"] == "job_posting"


def test_parse_job_rows_metadata_flags_linkedin():
    rows, _ = parse_job_rows(HiringCollector(), COMPANY, "q", SAMPLE_JOBS)
    meta = json.loads(rows[0]["metadata_json"])
    assert meta["is_linkedin"] is True
    assert meta["platform"] == "LinkedIn"


def test_job_source_prefers_apply_link_then_share_link():
    assert _job_source(SAMPLE_JOBS[0]) == "https://linkedin.com/jobs/1"
    assert _job_source(SAMPLE_JOBS[1]) == "https://google.com/share/2"


def test_parse_job_rows_empty():
    rows, linkedin = parse_job_rows(HiringCollector(), COMPANY, "q", [])
    assert rows == []
    assert linkedin == 0


def test_parse_job_rows_sets_source_date():
    jobs = [{"title": "ML Engineer", "detected_extensions": {"posted_at": "3 days ago"}}]
    rows, _ = parse_job_rows(HiringCollector(), COMPANY, "q", jobs, retrieval_date="2026-06-16")
    assert rows[0]["source_date"] == "3 days ago"
    meta = json.loads(rows[0]["metadata_json"])
    assert meta["date_provenance"] == DATE_PROVENANCE_ORIGIN


def test_parse_job_rows_source_date_retrieval_fallback():
    jobs = [{"title": "ML Engineer", "via": "via Indeed"}]
    rows, _ = parse_job_rows(HiringCollector(), COMPANY, "q", jobs, retrieval_date="2026-06-16")
    assert rows[0]["source_date"] == "2026-06-16"
    meta = json.loads(rows[0]["metadata_json"])
    assert meta["date_provenance"] == DATE_PROVENANCE_RETRIEVAL


def test_product_collect_without_api_key(conn, monkeypatch):
    monkeypatch.setattr(
        "evidence_collection.collectors.serpapi.settings",
        type("S", (), {"serpapi_api_key": ""})(),
    )
    ctx = CollectionContext(conn=conn, run_id=1, settings=settings)
    result = ProductServiceCollector().collect(ctx, COMPANY)
    assert result.status == CollectionStatus.API_KEY_MISSING


def test_hiring_collect_without_api_key(conn, monkeypatch):
    monkeypatch.setattr(
        "evidence_collection.collectors.serpapi.settings",
        type("S", (), {"serpapi_api_key": ""})(),
    )
    ctx = CollectionContext(conn=conn, run_id=1, settings=settings)
    result = HiringCollector().collect(ctx, COMPANY)
    assert result.status == CollectionStatus.API_KEY_MISSING


def test_make_evidence_refines_to_official_company_on_own_domain():
    from evidence_collection.collectors.serpapi import ProductServiceCollector

    company = {"ticker": "MSFT", "company_name": "Microsoft Corporation",
               "website_domain": "microsoft.com"}
    c = ProductServiceCollector()
    # A result on the company's own domain is a first-party claim -> official_company.
    own = c.make_evidence(company, evidence_text="AI", source_url="https://www.microsoft.com/ai")
    assert own["source_category"] == "official_company"
    assert own["source_reliability"] == "high"
    # A third-party result keeps the default (low-reliability news_article).
    third = c.make_evidence(company, evidence_text="AI", source_url="https://techblog.com/x")
    assert third["source_category"] == "news_article"
