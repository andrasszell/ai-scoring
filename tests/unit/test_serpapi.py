import json

from evidence_collection.collectors.serpapi import HiringCollector, parse_job_rows, _job_source

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
