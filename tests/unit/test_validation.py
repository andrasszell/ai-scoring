from evidence_collection.validation import is_valid_evidence, validate_evidence

BASE = {
    "ticker": "MSFT",
    "evidence_text": "machine learning",
    "collector_name": "sec_filings",
    "collector_version": "1.0.0",
    "source_url": "http://sec.gov/x",
}


def test_valid_row_passes():
    assert validate_evidence(BASE) == []
    assert is_valid_evidence(BASE)


def test_row_with_only_source_date_is_valid():
    row = {**BASE}
    del row["source_url"]
    row["source_date"] = "2026-01-01"
    assert is_valid_evidence(row)


def test_missing_source_url_and_date_fails():
    row = {**BASE}
    del row["source_url"]
    errors = validate_evidence(row)
    assert any("source_url and source_date" in e for e in errors)


def test_missing_required_fields_fail():
    assert "missing ticker" in validate_evidence({**BASE, "ticker": ""})
    assert "missing evidence_text" in validate_evidence({**BASE, "evidence_text": "  "})
    assert "missing collector_version" in validate_evidence({**BASE, "collector_version": None})
