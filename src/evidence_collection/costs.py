from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import yaml

from .registry_gate import platform_for_collector_name


def default_cost_estimates_path() -> Path:
    env_path = os.getenv("API_COST_ESTIMATES_YAML", "").strip()
    if env_path:
        return Path(env_path)
    project_root = Path(__file__).resolve().parents[2]
    candidate = project_root / "config" / "api_cost_estimates.yaml"
    if candidate.is_file():
        return candidate
    return Path.cwd() / "config" / "api_cost_estimates.yaml"


def load_cost_estimates(path: Path | None = None) -> dict[str, float]:
    """Load platform id → USD per API call estimates."""
    estimates_path = path or default_cost_estimates_path()
    if not estimates_path.is_file():
        return {}
    raw = yaml.safe_load(estimates_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"api_cost_estimates must be a mapping: {estimates_path}")
    platforms = raw.get("platforms") or {}
    if not isinstance(platforms, dict):
        raise ValueError(f"api_cost_estimates.platforms must be a mapping: {estimates_path}")
    out: dict[str, float] = {}
    for platform_id, value in platforms.items():
        if platform_id.startswith("#"):
            continue
        out[str(platform_id)] = float(value)
    return out


def _platform_id_for_collector(collector_name: str) -> str | None:
    platform = platform_for_collector_name(collector_name)
    return platform.id if platform is not None else None


def estimate_cost_usd(api_calls: int, platform_id: str | None, estimates: dict[str, float]) -> float:
    if not api_calls or not platform_id:
        return 0.0
    rate = estimates.get(platform_id, 0.0)
    return round(api_calls * rate, 4)


def summarize_run_costs(
    conn: sqlite3.Connection,
    run_id: int,
    estimates: dict[str, float] | None = None,
) -> dict:
    """Sum API calls and estimated USD for one collector run."""
    rates = estimates if estimates is not None else load_cost_estimates()
    rows = conn.execute(
        """
        SELECT collector_name, SUM(COALESCE(api_calls, 0)) AS api_calls
        FROM collector_status
        WHERE run_id = ?
        GROUP BY collector_name
        ORDER BY collector_name
        """,
        (run_id,),
    ).fetchall()
    by_collector: list[dict] = []
    total_calls = 0
    total_usd = 0.0
    for row in rows:
        calls = int(row["api_calls"] or 0)
        platform_id = _platform_id_for_collector(row["collector_name"])
        usd = estimate_cost_usd(calls, platform_id, rates)
        total_calls += calls
        total_usd += usd
        by_collector.append(
            {
                "collector_name": row["collector_name"],
                "platform_id": platform_id,
                "api_calls": calls,
                "estimated_usd": usd,
            }
        )
    return {
        "run_id": run_id,
        "total_api_calls": total_calls,
        "estimated_usd": round(total_usd, 4),
        "by_collector": by_collector,
    }


def format_cost_report(summary: dict) -> str:
    lines = [
        f"Run #{summary['run_id']} API cost estimate",
        f"  Total API calls: {summary['total_api_calls']}",
        f"  Estimated USD:   ${summary['estimated_usd']:.4f}",
        "",
        f"{'COLLECTOR':<20} {'PLATFORM':<22} {'CALLS':>8} {'USD':>10}",
    ]
    for row in summary["by_collector"]:
        platform = row["platform_id"] or "-"
        lines.append(
            f"{row['collector_name']:<20} {platform:<22} {row['api_calls']:>8} "
            f"${row['estimated_usd']:>9.4f}"
        )
    return "\n".join(lines)
