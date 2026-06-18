from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml

from .collectors.base import Collector


def default_ttl_path() -> Path:
    env_path = os.getenv("SOURCE_FRESHNESS_TTL_YAML", "").strip()
    if env_path:
        return Path(env_path)
    project_root = Path(__file__).resolve().parents[2]
    candidate = project_root / "config" / "source_freshness_ttl.yaml"
    if candidate.is_file():
        return candidate
    return Path.cwd() / "config" / "source_freshness_ttl.yaml"


def load_freshness_config(path: Path | None = None) -> tuple[int, dict[str, int]]:
    """Return (default_stale_days, source_type → TTL days)."""
    ttl_path = path or default_ttl_path()
    if not ttl_path.is_file():
        return 30, {}
    raw = yaml.safe_load(ttl_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"source_freshness_ttl must be a mapping: {ttl_path}")
    default_days = int(raw.get("default_stale_days") or 30)
    return default_days, load_source_ttl_days(ttl_path)


def policy_from_collect_args(args) -> FreshnessPolicy | None:
    """Build a freshness policy from collect CLI args, or None for full collect."""
    if getattr(args, "force", False):
        return FreshnessPolicy(force=True)
    stale_days = getattr(args, "stale_days", None)
    since_raw = getattr(args, "since", None)
    if stale_days is None and not since_raw:
        return None
    default_days, source_ttl = load_freshness_config()
    since = parse_since_date(since_raw) if since_raw else None
    return FreshnessPolicy(
        stale_days=stale_days,
        since=since,
        source_ttl_days=source_ttl,
        default_stale_days=default_days,
    )


def load_source_ttl_days(path: Path | None = None) -> dict[str, int]:
    """Load source_type → TTL days from config/source_freshness_ttl.yaml."""
    ttl_path = path or default_ttl_path()
    if not ttl_path.is_file():
        return {}
    raw = yaml.safe_load(ttl_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"source_freshness_ttl must be a mapping: {ttl_path}")
    source_types = raw.get("source_types") or {}
    if not isinstance(source_types, dict):
        raise ValueError(f"source_freshness_ttl.source_types must be a mapping: {ttl_path}")
    out: dict[str, int] = {}
    for source_type, days in source_types.items():
        if str(source_type).startswith("#"):
            continue
        out[str(source_type)] = int(days)
    return out


def parse_since_date(value: str) -> date:
    """Parse YYYY-MM-DD for ``--since``."""
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ValueError(f"Invalid --since date {value!r}; use YYYY-MM-DD") from exc


def parse_status_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    if " " in text and "T" not in text:
        text = text.replace(" ", "T", 1)
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class FreshnessPolicy:
    stale_days: int | None = None
    since: date | None = None
    force: bool = False
    source_ttl_days: dict[str, int] | None = None
    default_stale_days: int = 30

    @property
    def enabled(self) -> bool:
        return not self.force and (self.stale_days is not None or self.since is not None)

    def effective_ttl_days(self, source_type: str) -> int | None:
        if not self.enabled or self.stale_days is None:
            return None
        per_source = (self.source_ttl_days or {}).get(source_type)
        if per_source is not None:
            return max(per_source, self.stale_days)
        return self.stale_days

    def should_skip(
        self,
        *,
        source_type: str,
        last_collected_at: datetime | None,
        now: datetime | None = None,
    ) -> bool:
        if not self.enabled:
            return False
        if last_collected_at is None:
            return False
        current = now or datetime.now(timezone.utc)
        ttl_days = self.effective_ttl_days(source_type)
        if ttl_days is not None:
            age = current - last_collected_at
            if age < timedelta(days=ttl_days):
                return True
        if self.since is not None:
            since_dt = datetime.combine(self.since, datetime.min.time(), tzinfo=timezone.utc)
            if last_collected_at >= since_dt:
                return True
        return False


def plan_collection_targets(
    companies: list[dict],
    collectors: list[Collector],
    latest_status: dict[tuple[str, str], dict],
    policy: FreshnessPolicy,
) -> tuple[list[tuple[dict, Collector]], list[tuple[dict, Collector]]]:
    """Split (company, collector) pairs into run vs skip-fresh lists."""
    if not policy.enabled:
        targets = [(company, collector) for company in companies for collector in collectors]
        return targets, []

    run_targets: list[tuple[dict, Collector]] = []
    skip_targets: list[tuple[dict, Collector]] = []
    for company in companies:
        ticker = company["ticker"]
        for collector in collectors:
            key = (ticker, collector.name)
            row = latest_status.get(key)
            last_at = parse_status_timestamp(row.get("created_at") if row else None)
            if policy.should_skip(source_type=collector.source_type, last_collected_at=last_at):
                skip_targets.append((company, collector))
            else:
                run_targets.append((company, collector))
    return run_targets, skip_targets
