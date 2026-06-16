import json

from evidence_collection.collectors.serpapi import ProductServiceCollector
from evidence_collection.dates import DATE_PROVENANCE_ORIGIN, DATE_PROVENANCE_RETRIEVAL, web_result_date


COMPANY = {"ticker": "MSFT", "company_name": "Microsoft Corporation"}


def test_web_result_date_helpers():
    value, prov = web_result_date({"date": "Mar 10, 2024"}, fallback="2026-01-01")
    assert value == "Mar 10, 2024"
    assert prov == DATE_PROVENANCE_ORIGIN
    value, prov = web_result_date({}, fallback="2026-06-16")
    assert value == "2026-06-16"
    assert prov == DATE_PROVENANCE_RETRIEVAL


def test_product_evidence_includes_source_date_in_metadata():
    c = ProductServiceCollector()
    row = c.make_evidence(
        COMPANY,
        evidence_text="AI product",
        source_url="https://example.com/p",
        source_date="2026-06-16",
        metadata={"date_provenance": DATE_PROVENANCE_RETRIEVAL},
    )
    assert row["source_date"] == "2026-06-16"
    meta = json.loads(row["metadata_json"])
    assert meta["date_provenance"] == DATE_PROVENANCE_RETRIEVAL
