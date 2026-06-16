from evidence_collection.dates import (
    DATE_PROVENANCE_ORIGIN,
    DATE_PROVENANCE_QUARTER_ANCHOR,
    DATE_PROVENANCE_RETRIEVAL,
    collection_date_iso,
    job_posted_date,
    normalize_patent_date,
    normalize_publication_year,
    transcript_source_date,
    web_result_date,
)


def test_collection_date_iso():
    assert len(collection_date_iso()) == 10


def test_job_posted_date_from_detected_extensions():
    job = {"detected_extensions": {"posted_at": "3 days ago"}}
    value, prov = job_posted_date(job, fallback="2026-01-01")
    assert value == "3 days ago"
    assert prov == DATE_PROVENANCE_ORIGIN


def test_job_posted_date_falls_back_to_retrieval():
    value, prov = job_posted_date({}, fallback="2026-06-16")
    assert value == "2026-06-16"
    assert prov == DATE_PROVENANCE_RETRIEVAL


def test_web_result_date_uses_origin_when_present():
    value, prov = web_result_date({"date": "Mar 10, 2024"}, fallback="2026-01-01")
    assert value == "Mar 10, 2024"
    assert prov == DATE_PROVENANCE_ORIGIN


def test_normalize_publication_year():
    value, prov = normalize_publication_year(2023)
    assert value == "2023-01-01"
    assert prov == DATE_PROVENANCE_ORIGIN


def test_normalize_publication_year_missing():
    value, prov = normalize_publication_year(None)
    assert prov == DATE_PROVENANCE_RETRIEVAL


def test_normalize_patent_date():
    value, prov = normalize_patent_date("2019-04-02")
    assert value == "2019-04-02"
    assert prov == DATE_PROVENANCE_ORIGIN


def test_transcript_source_date_prefers_item_date():
    value, prov = transcript_source_date({"date": "2024-05-01"}, year=2024, quarter=1)
    assert value == "2024-05-01"
    assert prov == DATE_PROVENANCE_ORIGIN


def test_transcript_source_date_quarter_fallback():
    value, prov = transcript_source_date({}, year=2024, quarter=2)
    assert value == "2024-06-01"
    assert prov == DATE_PROVENANCE_QUARTER_ANCHOR
