from datetime import datetime, timedelta, timezone

import pytest

from evidence_collection.collectors.sec_filings import SecFilingsCollector
from evidence_collection.freshness import (
    FreshnessPolicy,
    load_freshness_config,
    parse_since_date,
    parse_status_timestamp,
    plan_collection_targets,
    policy_from_collect_args,
)


def test_load_freshness_config():
    default_days, source_ttl = load_freshness_config()
    assert default_days == 30
    assert source_ttl["sec_annual_filing"] == 90
    assert source_ttl["job_posting"] == 14


def test_parse_since_date():
    assert parse_since_date("2026-06-01").isoformat() == "2026-06-01"
    with pytest.raises(ValueError, match="Invalid --since"):
        parse_since_date("06-01-2026")


def test_should_skip_within_stale_days():
    policy = FreshnessPolicy(stale_days=30)
    now = datetime(2026, 6, 16, tzinfo=timezone.utc)
    last = now - timedelta(days=5)
    assert policy.should_skip(source_type="job_posting", last_collected_at=last, now=now) is True


def test_should_collect_when_stale():
    policy = FreshnessPolicy(stale_days=30)
    now = datetime(2026, 6, 16, tzinfo=timezone.utc)
    last = now - timedelta(days=45)
    assert policy.should_skip(source_type="job_posting", last_collected_at=last, now=now) is False


def test_should_collect_when_never_run():
    policy = FreshnessPolicy(stale_days=30)
    assert policy.should_skip(source_type="job_posting", last_collected_at=None) is False


def test_per_source_ttl_wins_over_shorter_cli():
    policy = FreshnessPolicy(stale_days=30, source_ttl_days={"sec_annual_filing": 90})
    now = datetime(2026, 6, 16, tzinfo=timezone.utc)
    last = now - timedelta(days=45)
    assert policy.should_skip(source_type="sec_annual_filing", last_collected_at=last, now=now) is True
    assert policy.should_skip(source_type="job_posting", last_collected_at=last, now=now) is False


def test_since_date_skips_recent():
    policy = FreshnessPolicy(since=parse_since_date("2026-06-01"))
    last = datetime(2026, 6, 10, tzinfo=timezone.utc)
    assert policy.should_skip(source_type="job_posting", last_collected_at=last) is True


def test_since_only_ignores_per_source_ttl():
    """--since without --stale-days must not apply config TTL (only the date cutoff)."""
    _, source_ttl = load_freshness_config()
    policy = FreshnessPolicy(since=parse_since_date("2026-06-01"), source_ttl_days=source_ttl)
    now = datetime(2026, 6, 16, tzinfo=timezone.utc)
    last = datetime(2026, 5, 20, tzinfo=timezone.utc)
    assert policy.should_skip(source_type="sec_annual_filing", last_collected_at=last, now=now) is False


def test_plan_collection_targets_splits():
    companies = [{"ticker": "MSFT", "company_name": "Microsoft"}]
    collectors = [SecFilingsCollector()]
    now = datetime(2026, 6, 16, tzinfo=timezone.utc)
    latest = {
        ("MSFT", "sec_filings"): {
            "created_at": (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
        }
    }
    policy = FreshnessPolicy(stale_days=30)
    run_targets, skip_targets = plan_collection_targets(companies, collectors, latest, policy)
    assert len(skip_targets) == 1
    assert len(run_targets) == 0


def test_policy_from_collect_args_none_by_default():
    args = type("Args", (), {"force": False, "stale_days": None, "since": None})()
    assert policy_from_collect_args(args) is None


def test_policy_from_collect_args_stale_days():
    args = type("Args", (), {"force": False, "stale_days": 14, "since": None})()
    policy = policy_from_collect_args(args)
    assert policy is not None
    assert policy.enabled is True
    assert policy.stale_days == 14


def test_parse_status_timestamp_sqlite_format():
    parsed = parse_status_timestamp("2026-06-16 16:22:12")
    assert parsed is not None
    assert parsed.year == 2026
