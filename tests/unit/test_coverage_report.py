from evidence_collection.coverage_report import build_coverage_report, format_coverage_report
from evidence_collection.db import repository as repo
from evidence_collection.models import CollectorResult
from evidence_collection.status import CollectionStatus


def test_build_coverage_report_gaps(conn):
    repo.upsert_companies(
        conn,
        [
            {"ticker": "MSFT", "company_name": "Microsoft"},
            {"ticker": "NVDA", "company_name": "NVIDIA"},
        ],
    )
    conn.execute(
        """
        INSERT INTO evidence_items(
            ticker, source_type, source_url, evidence_text, collector_name, collector_version,
            source_category, source_reliability, raw_hash, confidence_initial
        ) VALUES ('MSFT', 'sec_annual_filing', 'https://example.com', 'AI text',
                  'sec_filings', '1.0.0', 'regulatory_filing', 'high', 'h1', 0.75)
        """
    )
    conn.commit()

    run_id = repo.start_run(conn, "seed", {})
    repo.record_status(
        conn,
        run_id=run_id,
        ticker="NVDA",
        source_type="sec_annual_filing",
        collector_name="sec_filings",
        collector_version="1.0.0",
        result=CollectorResult(CollectionStatus.NO_RESULTS, message="reason:source_empty"),
        duration_seconds=1.0,
    )
    repo.finish_run(conn, run_id)

    companies = repo.get_companies(conn)
    report = build_coverage_report(conn, companies)
    sec = report["summary"]["sec_annual_filing"]
    assert sec["with_evidence"] == 1
    assert sec["without_evidence"] == 1
    assert "NVDA" in sec["missing_tickers"]
    assert any(g["ticker"] == "NVDA" and g["source_type"] == "sec_annual_filing" for g in report["gaps"])


def test_format_coverage_report_missing_only():
    report = {
        "generated_at": "2026-06-19T00:00:00+00:00",
        "companies_total": 2,
        "source_types": ["sec_annual_filing", "patent"],
        "summary": {
            "sec_annual_filing": {
                "with_evidence": 1,
                "without_evidence": 1,
                "missing_tickers": ["NVDA"],
            },
            "patent": {
                "with_evidence": 2,
                "without_evidence": 0,
                "missing_tickers": [],
            },
        },
    }
    text = format_coverage_report(report, missing_only=True)
    assert "sec_annual_filing" in text
    assert "NVDA" in text
    assert "patent" not in text
