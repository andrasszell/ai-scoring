from evidence_collection.dates import (
    DATE_PROVENANCE_ORIGIN,
    DATE_PROVENANCE_QUARTER_ANCHOR,
    normalize_patent_date,
    normalize_publication_year,
    transcript_source_date,
)


def test_patent_date_normalization():
    value, prov = normalize_patent_date("2019-04-02")
    assert value == "2019-04-02"
    assert prov == "origin"


def test_patent_date_missing_uses_retrieval():
    value, prov = normalize_patent_date(None)
    assert len(value) == 10
    assert prov == "retrieval"


def test_research_year_normalization():
    value, prov = normalize_publication_year(2021)
    assert value == "2021-01-01"
    assert prov == "origin"


def test_transcript_source_date_quarter_anchor():
    value, prov = transcript_source_date({}, year=2023, quarter=4)
    assert value == "2023-12-01"
    assert prov == DATE_PROVENANCE_QUARTER_ANCHOR
