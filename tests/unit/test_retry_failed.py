from evidence_collection.collectors import COLLECTOR_BY_NAME, REGISTRY
from evidence_collection.db import repository as repo
from evidence_collection.models import CollectorResult
from evidence_collection.retry import build_retry_targets, format_retry_plan, retry_failed_collection
from evidence_collection.status import CollectionStatus


def _seed_company(conn, ticker: str = "MSFT") -> None:
    repo.upsert_companies(
        conn,
        [{"ticker": ticker, "company_name": "Microsoft Corp", "cik": "0000789019"}],
    )


def _record_status(conn, *, run_id: int, ticker: str, collector_name: str, status: str) -> None:
    repo.record_status(
        conn,
        run_id=run_id,
        ticker=ticker,
        source_type="test_source",
        collector_name=collector_name,
        collector_version="1.0.0",
        result=CollectorResult(status),
        duration_seconds=0.1,
    )


def test_failed_status_rows_returns_latest_retryable(conn):
    _seed_company(conn)
    run1 = repo.start_run(conn, "test", {})
    _record_status(conn, run_id=run1, ticker="MSFT", collector_name="research", status=CollectionStatus.SUCCESS)
    repo.finish_run(conn, run1)
    run2 = repo.start_run(conn, "test", {})
    _record_status(conn, run_id=run2, ticker="MSFT", collector_name="research", status=CollectionStatus.RATE_LIMITED)
    repo.finish_run(conn, run2)

    rows = repo.failed_status_rows(conn)
    assert len(rows) == 1
    assert rows[0]["ticker"] == "MSFT"
    assert rows[0]["collector_name"] == "research"
    assert rows[0]["status"] == CollectionStatus.RATE_LIMITED


def test_failed_status_rows_ignores_success_latest(conn):
    _seed_company(conn)
    run1 = repo.start_run(conn, "test", {})
    _record_status(conn, run_id=run1, ticker="MSFT", collector_name="research", status=CollectionStatus.RATE_LIMITED)
    repo.finish_run(conn, run1)
    run2 = repo.start_run(conn, "test", {})
    _record_status(conn, run_id=run2, ticker="MSFT", collector_name="research", status=CollectionStatus.SUCCESS)
    repo.finish_run(conn, run2)

    assert repo.failed_status_rows(conn) == []


def test_build_retry_targets_filters_by_source(conn):
    _seed_company(conn)
    rows = [
        {"ticker": "MSFT", "collector_name": "research", "status": CollectionStatus.RATE_LIMITED},
        {"ticker": "MSFT", "collector_name": "product_docs", "status": CollectionStatus.SOURCE_UNAVAILABLE},
    ]
    targets = build_retry_targets(conn, rows, source_keys=["research"])
    assert len(targets) == 1
    assert targets[0][1].name == "research"


def test_format_retry_plan_empty():
    assert "No retryable" in format_retry_plan([])


def test_retry_failed_collection_runs_targets(conn, monkeypatch):
    _seed_company(conn)
    run_id = repo.start_run(conn, "test", {})
    _record_status(
        conn,
        run_id=run_id,
        ticker="MSFT",
        collector_name="research",
        status=CollectionStatus.RATE_LIMITED,
    )
    repo.finish_run(conn, run_id)

    calls: list[str] = []

    class FakeResearch:
        name = "research"
        version = "1.0.0"
        source_type = "research_paper"
        platform_id = "semantic_scholar"

        def collect(self, ctx, company):
            calls.append(company["ticker"])
            return CollectorResult(CollectionStatus.SUCCESS, evidence_count=2, api_calls=1)

    monkeypatch.setitem(REGISTRY, "research", FakeResearch())
    monkeypatch.setitem(COLLECTOR_BY_NAME, "research", FakeResearch())

    rows, totals = retry_failed_collection(conn, source_keys=["research"])
    assert len(rows) == 1
    assert calls == ["MSFT"]
    assert totals["ok"] == 1
    assert totals["evidence"] == 2
