from datetime import datetime, timedelta, timezone

from evidence_collection.db import repository as repo
from evidence_collection.freshness_report import (
    build_freshness_report,
    format_freshness_report,
    write_freshness_report,
)
from evidence_collection.models import CollectorResult
from evidence_collection.status import CollectionStatus


def _seed_company(conn, ticker="MSFT", name="Microsoft"):
    repo.upsert_companies(conn, [{"ticker": ticker, "company_name": name}])


def _seed_status(conn, *, ticker, source_type, collector_name, status, days_ago=1):
    run_id = repo.start_run(conn, "seed", {})
    repo.record_status(
        conn,
        run_id=run_id,
        ticker=ticker,
        source_type=source_type,
        collector_name=collector_name,
        collector_version="1.0.0",
        result=CollectorResult(CollectionStatus.SUCCESS if status == "success" else CollectionStatus.SOURCE_UNAVAILABLE),
        duration_seconds=1.0,
    )
    repo.finish_run(conn, run_id)
    ts = (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "UPDATE collector_status SET status=?, created_at=? WHERE run_id=?",
        (status, ts, run_id),
    )
    conn.commit()


def _seed_evidence(conn, *, ticker, source_type, collector_name, days_ago=1):
    _seed_company(conn, ticker)
    ts = (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        """
        INSERT INTO evidence_items(
            ticker, source_type, source_url, evidence_text, collector_name, collector_version,
            created_at
        ) VALUES (?, ?, 'https://example.com', 'text', ?, '1.0.0', ?)
        """,
        (ticker, source_type, collector_name, ts),
    )
    conn.commit()


def test_build_freshness_report_flags_stale_company(conn):
    now = datetime(2026, 6, 16, tzinfo=timezone.utc)
    _seed_company(conn)
    _seed_evidence(conn, ticker="MSFT", source_type="sec_annual_filing", collector_name="sec_filings", days_ago=45)
    _seed_status(
        conn,
        ticker="MSFT",
        source_type="sec_annual_filing",
        collector_name="sec_filings",
        status="success",
        days_ago=2,
    )
    companies = repo.get_companies(conn, ["MSFT"])
    report = build_freshness_report(conn, companies, stale_days=30, now=now)
    assert report["summary"]["companies_total"] == 1
    assert report["companies"][0]["is_stale"] is True
    assert report["companies"][0]["stale_reason"] == "past_threshold"


def test_build_freshness_report_no_evidence_is_stale(conn):
    now = datetime(2026, 6, 16, tzinfo=timezone.utc)
    _seed_company(conn, "NVDA", "NVIDIA")
    companies = repo.get_companies(conn, ["NVDA"])
    report = build_freshness_report(conn, companies, stale_days=30, now=now)
    assert report["companies"][0]["is_stale"] is True
    assert report["companies"][0]["stale_reason"] == "no_evidence"


def test_build_freshness_report_source_past_sla(conn):
    now = datetime(2026, 6, 16, tzinfo=timezone.utc)
    _seed_company(conn)
    _seed_evidence(conn, ticker="MSFT", source_type="job_posting", collector_name="hiring_jobs", days_ago=2)
    _seed_status(
        conn,
        ticker="MSFT",
        source_type="job_posting",
        collector_name="hiring_jobs",
        status="success",
        days_ago=20,
    )
    companies = repo.get_companies(conn, ["MSFT"])
    report = build_freshness_report(conn, companies, now=now)
    source = report["companies"][0]["sources"][0]
    assert source["source_type"] == "job_posting"
    assert source["is_stale"] is True
    assert source["stale_reason"] == "past_sla"
    assert source["sla_days"] == 14


def test_format_freshness_report_stale_only(conn):
    now = datetime(2026, 6, 16, tzinfo=timezone.utc)
    _seed_company(conn)
    _seed_company(conn, "NVDA", "NVIDIA")
    _seed_evidence(conn, ticker="MSFT", source_type="sec_annual_filing", collector_name="sec_filings", days_ago=1)
    _seed_status(
        conn,
        ticker="MSFT",
        source_type="sec_annual_filing",
        collector_name="sec_filings",
        status="success",
        days_ago=1,
    )
    companies = repo.get_companies(conn)
    report = build_freshness_report(conn, companies, stale_days=30, now=now)
    text = format_freshness_report(report, stale_only=True)
    assert "NVDA" in text
    assert "Stale companies" in text


def test_write_freshness_report(tmp_path, conn):
    now = datetime(2026, 6, 16, tzinfo=timezone.utc)
    _seed_company(conn)
    companies = repo.get_companies(conn)
    report = build_freshness_report(conn, companies, now=now)
    out = tmp_path / "freshness.json"
    write_freshness_report(out, report)
    assert out.is_file()
    assert '"companies_total"' in out.read_text(encoding="utf-8")
