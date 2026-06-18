from datetime import datetime, timedelta, timezone

from evidence_collection.collectors import REGISTRY
from evidence_collection.db import repository as repo
from evidence_collection.freshness import FreshnessPolicy
from evidence_collection.models import CollectorResult
from evidence_collection.runner import run_collection
from evidence_collection.status import CollectionStatus


def test_run_collection_skips_fresh_pairs(conn, monkeypatch):
    repo.upsert_companies(conn, [{"ticker": "MSFT", "company_name": "Microsoft Corp"}])

    class FakeSec:
        name = "sec_filings"
        version = "1.0.0"
        source_type = "sec_annual_filing"
        platform_id = "sec_edgar"

        def collect(self, ctx, company):
            raise AssertionError("should not collect when fresh")

    monkeypatch.setitem(REGISTRY, "sec", FakeSec())

    run_id = repo.start_run(conn, "seed", {})
    repo.record_status(
        conn,
        run_id=run_id,
        ticker="MSFT",
        source_type="sec_annual_filing",
        collector_name="sec_filings",
        collector_version="1.0.0",
        result=CollectorResult(CollectionStatus.SUCCESS, evidence_count=1),
        duration_seconds=1.0,
    )
    repo.finish_run(conn, run_id)
    conn.execute(
        "UPDATE collector_status SET created_at = ? WHERE run_id = ?",
        ((datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"), run_id),
    )
    conn.commit()

    policy = FreshnessPolicy(stale_days=30)
    totals = run_collection(
        conn,
        [{"ticker": "MSFT", "company_name": "Microsoft Corp"}],
        [FakeSec()],
        command="collect",
        args={"stale_days": 30},
        freshness_policy=policy,
    )
    assert totals["skipped"] == 1
    assert totals["ok"] == 0
    assert totals["evidence"] == 0
