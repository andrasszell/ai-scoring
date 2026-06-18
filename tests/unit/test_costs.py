import pytest

from evidence_collection.costs import (
    estimate_cost_usd,
    format_cost_report,
    load_cost_estimates,
    summarize_run_costs,
)
from evidence_collection.models import CollectorResult
from evidence_collection.status import CollectionStatus
from evidence_collection.db import repository as repo


def test_load_cost_estimates_has_phase1_platforms():
    rates = load_cost_estimates()
    assert rates["sec_edgar"] == 0.0
    assert rates["serpapi_web"] > 0
    assert rates["press_releases"] > 0


def test_estimate_cost_usd():
    rates = {"serpapi_web": 0.01}
    assert estimate_cost_usd(10, "serpapi_web", rates) == 0.1
    assert estimate_cost_usd(0, "serpapi_web", rates) == 0.0
    assert estimate_cost_usd(5, None, rates) == 0.0


def test_summarize_run_costs(conn):
    run_id = repo.start_run(conn, "test", {})
    repo.record_status(
        conn,
        run_id=run_id,
        ticker="MSFT",
        source_type="web_search_product",
        collector_name="web_products",
        collector_version="1.0.0",
        result=CollectorResult(CollectionStatus.SUCCESS, api_calls=3),
        duration_seconds=1.0,
    )
    repo.record_status(
        conn,
        run_id=run_id,
        ticker="MSFT",
        source_type="sec_annual_filing",
        collector_name="sec_filings",
        collector_version="1.0.0",
        result=CollectorResult(CollectionStatus.SUCCESS, api_calls=2),
        duration_seconds=1.0,
    )
    rates = {"serpapi_web": 0.01, "sec_edgar": 0.0}
    summary = summarize_run_costs(conn, run_id, estimates=rates)
    assert summary["total_api_calls"] == 5
    assert summary["estimated_usd"] == 0.03
    text = format_cost_report(summary)
    assert "web_products" in text
    assert "$0.0300" in text or "$0.03" in text


def test_format_cost_report_empty_collectors():
    text = format_cost_report(
        {"run_id": 1, "total_api_calls": 0, "estimated_usd": 0.0, "by_collector": []}
    )
    assert "Run #1" in text
