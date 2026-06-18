from __future__ import annotations

import time

from .collectors.base import Collector
from .registry_gate import collector_gate
from .config import settings
from .db import repository as repo
from .logging_config import get_logger
from .models import CollectionContext, CollectorResult
from .status import CollectionStatus

logger = get_logger("evidence_collection.runner")


def _execute_collector(
    conn,
    *,
    run_id: int,
    company: dict,
    collector: Collector,
    totals: dict,
) -> None:
    ticker = company["ticker"]
    ctx = CollectionContext(conn=conn, run_id=run_id, settings=settings)
    started = time.time()
    try:
        blocked = collector_gate(collector)
        result = blocked if blocked is not None else collector.collect(ctx, company)
    except Exception as exc:  # noqa: BLE001 - never abort a run
        logger.exception("collector %s failed for %s", collector.name, ticker)
        result = CollectorResult(CollectionStatus.SOURCE_UNAVAILABLE, message=f"unhandled: {exc}")
    duration = time.time() - started
    repo.record_status(
        conn,
        run_id=run_id,
        ticker=ticker,
        source_type=collector.source_type,
        collector_name=collector.name,
        collector_version=collector.version,
        result=result,
        duration_seconds=round(duration, 3),
    )
    totals["evidence"] += result.evidence_count
    totals["documents"] += result.documents_count
    if result.status in (CollectionStatus.SUCCESS, CollectionStatus.NO_RESULTS):
        totals["ok"] += 1
    else:
        totals["failed"] += 1
    logger.info(
        "%s %s -> %s (%d evidence, %.2fs)%s",
        ticker, collector.name, result.status, result.evidence_count, duration,
        f" — {result.storage_message()}" if result.storage_message() else "",
    )


def _finalize_run(conn, *, run_id: int, command: str, totals: dict, run_started: float) -> dict:
    runtime = round(time.time() - run_started, 2)
    repo.upsert_collection_metric(conn, run_id=run_id, ticker=None,
                                name="collection_runtime_seconds", value=runtime, source=command)
    repo.upsert_collection_metric(conn, run_id=run_id, ticker=None,
                                  name="documents_collected_count", value=float(totals["documents"]), source=command)
    repo.upsert_collection_metric(conn, run_id=run_id, ticker=None,
                                  name="evidence_items_collected_count", value=float(totals["evidence"]), source=command)
    from .costs import summarize_run_costs

    cost_summary = summarize_run_costs(conn, run_id)
    repo.upsert_collection_metric(
        conn, run_id=run_id, ticker=None,
        name="estimated_api_cost_usd", value=cost_summary["estimated_usd"], source=command,
    )
    repo.upsert_collection_metric(
        conn, run_id=run_id, ticker=None,
        name="total_api_calls", value=float(cost_summary["total_api_calls"]), source=command,
    )
    totals["estimated_api_cost_usd"] = cost_summary["estimated_usd"]
    totals["total_api_calls"] = cost_summary["total_api_calls"]
    repo.finish_run(conn, run_id, status="completed")
    totals["run_id"] = run_id
    totals["runtime_seconds"] = runtime
    return totals


def run_targeted_collection(
    conn,
    targets: list[tuple[dict, Collector]],
    *,
    command: str,
    args: dict,
) -> dict:
    """Execute specific (company, collector) pairs — used by retry-failed."""
    run_id = repo.start_run(conn, command, args)
    totals = {"evidence": 0, "documents": 0, "ok": 0, "failed": 0}
    run_started = time.time()
    for company, collector in targets:
        _execute_collector(conn, run_id=run_id, company=company, collector=collector, totals=totals)
    return _finalize_run(conn, run_id=run_id, command=command, totals=totals, run_started=run_started)


def run_collection(
    conn,
    companies: list[dict],
    collectors: list[Collector],
    *,
    command: str,
    args: dict,
) -> dict:
    """Execute collectors over companies, recording status for every (company, source).

    A single collector failure is captured as a status row, never propagated, so
    the run always completes and the inference team can see exactly what happened.
    """
    run_id = repo.start_run(conn, command, args)
    totals = {"evidence": 0, "documents": 0, "ok": 0, "failed": 0}
    run_started = time.time()

    for company in companies:
        for collector in collectors:
            _execute_collector(conn, run_id=run_id, company=company, collector=collector, totals=totals)

    return _finalize_run(conn, run_id=run_id, command=command, totals=totals, run_started=run_started)
