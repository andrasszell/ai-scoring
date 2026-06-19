from evidence_collection.db import repository as repo
from evidence_collection.snapshot import create_snapshot


def test_create_snapshot_writes_manifest(conn, tmp_path):
    repo.upsert_companies(conn, [{"ticker": "MSFT", "company_name": "Microsoft"}])
    conn.execute(
        """
        INSERT INTO evidence_items(
            ticker, source_type, source_url, evidence_text, collector_name, collector_version,
            source_category, source_reliability, raw_hash, confidence_initial
        ) VALUES ('MSFT', 'sec_annual_filing', 'https://example.com', 'AI paragraph',
                  'sec_filings', '1.0.0', 'regulatory_filing', 'high', 'abc', 0.75)
        """
    )
    conn.commit()

    result = create_snapshot(conn, tmp_path / "snap", tag="test")
    manifest_path = tmp_path / "snap" / "manifest.json"
    assert manifest_path.is_file()
    assert result["manifest"]["tag"] == "test"
    assert result["manifest"]["validate"]["total_evidence"] == 1
    assert result["counts"]["evidence_items.jsonl"] == 1
    assert (tmp_path / "snap" / "companies.csv").is_file()
