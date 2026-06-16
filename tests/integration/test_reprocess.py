from pathlib import Path

from evidence_collection.db import repository as repo
from evidence_collection.reprocess import reprocess_documents

FIXTURE = Path(__file__).parent.parent / "fixtures" / "sample_filing.txt"


def test_reprocess_rebuilds_evidence_from_stored_text(conn, tmp_path):
    repo.upsert_companies(conn, [{"ticker": "TEST", "company_name": "Test Industrials Inc."}])
    # Simulate a previously collected & stored document.
    text_path = tmp_path / "filing.txt"
    text_path.write_text(FIXTURE.read_text(), encoding="utf-8")
    repo.insert_document(conn, {
        "ticker": "TEST",
        "source_type": "sec_annual_filing",
        "source_url": "http://sec.gov/test",
        "source_date": "2026-01-01",
        "text_path": str(text_path),
        "content_hash": "abc",
    })

    totals = reprocess_documents(conn, sources=["sec"], tickers=["TEST"])
    assert totals["documents"] == 1
    assert totals["evidence"] >= 2

    rows = conn.execute("SELECT * FROM evidence_items WHERE ticker='TEST'").fetchall()
    assert rows
    first = dict(rows[0])
    assert first["raw_document_id"] is not None      # traceable to the document
    assert first["source_url"] == "http://sec.gov/test"
    # Reprocess is idempotent (delete-then-insert) — running again keeps the count stable.
    again = reprocess_documents(conn, sources=["sec"], tickers=["TEST"])
    assert again["evidence"] == totals["evidence"]


def test_reprocess_skips_missing_text_files(conn):
    repo.upsert_companies(conn, [{"ticker": "TEST", "company_name": "Test Inc."}])
    repo.insert_document(conn, {
        "ticker": "TEST", "source_type": "sec_annual_filing",
        "source_url": "http://sec.gov/x", "text_path": "/nonexistent/path.txt", "content_hash": "z",
    })
    totals = reprocess_documents(conn, sources=["sec"], tickers=["TEST"])
    assert totals["skipped_missing_text"] == 1
    assert totals["evidence"] == 0
