from evidence_collection.collectors.base import Collector
from evidence_collection.db import repository as repo
from evidence_collection.models import CollectorResult
from evidence_collection.runner import run_collection
from evidence_collection.status import CollectionStatus


class _OkCollector(Collector):
    name = "ok"
    version = "1.0.0"
    source_type = "test_ok"

    def collect(self, ctx, company):
        repo.insert_evidence(ctx.conn, [self.make_evidence(
            company, evidence_text="machine learning", source_url="http://src/ok")])
        return CollectorResult(CollectionStatus.SUCCESS, evidence_count=1)


class _BoomCollector(Collector):
    name = "boom"
    version = "1.0.0"
    source_type = "test_boom"

    def collect(self, ctx, company):
        raise RuntimeError("kaboom")


def test_run_records_status_for_every_source_and_survives_failures(conn):
    repo.upsert_companies(conn, [{"ticker": "MSFT", "company_name": "Microsoft Corporation"}])
    company = repo.get_companies(conn, ["MSFT"])[0]

    totals = run_collection(
        conn, [company], [_OkCollector(), _BoomCollector()],
        command="test", args={},
    )
    assert totals["evidence"] == 1

    summary = {r["source_type"]: r["status"] for r in repo.status_summary(conn, ["MSFT"])}
    assert summary["test_ok"] == CollectionStatus.SUCCESS
    # The crashing collector is captured as a status row, not propagated.
    assert summary["test_boom"] == CollectionStatus.SOURCE_UNAVAILABLE


def test_run_writes_operational_metrics(conn):
    repo.upsert_companies(conn, [{"ticker": "MSFT", "company_name": "Microsoft Corporation"}])
    company = repo.get_companies(conn, ["MSFT"])[0]
    run_collection(conn, [company], [_OkCollector()], command="test", args={})
    names = {r["metric_name"] for r in conn.execute("SELECT metric_name FROM collection_metrics")}
    assert "collection_runtime_seconds" in names
    assert "evidence_items_collected_count" in names
