from evidence_collection.db import repository as repo
from evidence_collection.models import CollectorResult, collector_result
from evidence_collection.outcomes import OutcomeReason
from evidence_collection.status import CollectionStatus


def _company():
    return {"ticker": "MSFT", "company_name": "Microsoft Corporation", "sector": "Tech"}


def _evidence(ticker="MSFT", collector="sec_filings", text="machine learning",
              source_url="http://sec.gov/x", raw_hash=None):
    return {
        "ticker": ticker,
        "company_name": "Microsoft Corporation",
        "source_type": "sec_annual_filing",
        "evidence_text": text,
        "collector_name": collector,
        "collector_version": "1.0.0",
        "source_url": source_url,
        "raw_hash": raw_hash,
    }


def test_upsert_companies_sets_company_id_default(conn):
    repo.upsert_companies(conn, [_company()])
    rows = repo.get_companies(conn, ["MSFT"])
    assert rows[0]["company_id"] == "MSFT"
    assert rows[0]["company_name"] == "Microsoft Corporation"


def test_delete_evidence_is_scoped_to_collector(conn):
    repo.upsert_companies(conn, [_company()])
    repo.insert_evidence(conn, [_evidence(collector="sec_filings")])
    repo.insert_evidence(conn, [_evidence(collector="research", text="LLM research paper")])
    # Deleting one collector leaves the other intact (idempotent re-runs).
    repo.delete_evidence(conn, "MSFT", "sec_filings")
    remaining = conn.execute("SELECT collector_name FROM evidence_items").fetchall()
    assert [r["collector_name"] for r in remaining] == ["research"]


def test_record_status_and_summary(conn):
    repo.upsert_companies(conn, [_company()])
    run_id = repo.start_run(conn, "collect", {"tickers": ["MSFT"]})
    repo.record_status(
        conn, run_id=run_id, ticker="MSFT", source_type="sec_annual_filing",
        collector_name="sec_filings", collector_version="1.0.0",
        result=collector_result(
            CollectionStatus.NO_RESULTS,
            outcome_reason=OutcomeReason.SOURCE_EMPTY,
            message="no filing",
            source_hits=0,
            candidates_after_filter=0,
        ),
        duration_seconds=0.1,
    )
    repo.finish_run(conn, run_id)
    summary = repo.status_summary(conn, ["MSFT"])
    assert summary[0]["status"] == CollectionStatus.NO_RESULTS
    assert summary[0]["message"] == "reason:source_empty — no filing"
    assert summary[0]["source_hits"] == 0


def test_quality_report_flags_missing_outcome_reason(conn):
    repo.upsert_companies(conn, [_company()])
    run_id = repo.start_run(conn, "collect", {"tickers": ["MSFT"]})
    repo.record_status(
        conn, run_id=run_id, ticker="MSFT", source_type="job_posting",
        collector_name="hiring_jobs", collector_version="1.0.0",
        result=CollectorResult(CollectionStatus.NO_RESULTS, message="legacy message"),
        duration_seconds=0.1,
    )
    report = repo.quality_report(conn)
    assert report["violations"]["missing_outcome_reason"] == 1


def test_insert_evidence_rejects_rows_without_source_anchor(conn):
    repo.upsert_companies(conn, [_company()])
    bad = _evidence(source_url=None)  # no source_url and no source_date -> §22 violation
    bad.pop("source_url")
    inserted = repo.insert_evidence(conn, [bad])
    assert inserted == 0
    assert conn.execute("SELECT COUNT(*) AS n FROM evidence_items").fetchone()["n"] == 0


def test_insert_evidence_dedups_by_raw_hash(conn):
    repo.upsert_companies(conn, [_company()])
    rows = [
        _evidence(text="same", raw_hash="HASH1"),
        _evidence(text="same again", raw_hash="HASH1"),  # duplicate hash -> skipped
        _evidence(text="different", raw_hash="HASH2"),
    ]
    inserted = repo.insert_evidence(conn, rows)
    assert inserted == 2
    # Re-inserting the same hash later is also skipped (idempotent across calls).
    assert repo.insert_evidence(conn, [_evidence(text="x", raw_hash="HASH1")]) == 0


def test_insert_document_dedups_by_content_hash(conn):
    repo.upsert_companies(conn, [_company()])
    id1 = repo.insert_document(conn, {"ticker": "MSFT", "source_type": "sec_annual_filing",
                                      "source_url": "http://a", "content_hash": "CH1"})
    # Same content at a different URL reuses the existing document.
    id2 = repo.insert_document(conn, {"ticker": "MSFT", "source_type": "sec_annual_filing",
                                      "source_url": "http://b", "content_hash": "CH1"})
    assert id1 == id2


def test_insert_document_is_upsert(conn):
    repo.upsert_companies(conn, [_company()])
    doc = {"ticker": "MSFT", "source_type": "sec_annual_filing", "source_url": "http://x", "title": "v1"}
    id1 = repo.insert_document(conn, doc)
    doc["title"] = "v2"
    id2 = repo.insert_document(conn, doc)
    assert id1 == id2
    row = conn.execute("SELECT title FROM documents WHERE id=?", (id1,)).fetchone()
    assert row["title"] == "v2"
