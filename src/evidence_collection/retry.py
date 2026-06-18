from __future__ import annotations

import sqlite3

from .collectors import COLLECTOR_BY_NAME, REGISTRY
from .db import repository as repo
from .runner import run_targeted_collection


def build_retry_targets(
    conn: sqlite3.Connection,
    rows: list[dict],
    *,
    source_keys: list[str] | None = None,
) -> list[tuple[dict, object]]:
    """Resolve failed status rows to (company, collector) pairs for re-run."""
    if not rows:
        return []
    allowed_collectors: set[str] | None = None
    if source_keys:
        unknown = [s for s in source_keys if s not in REGISTRY]
        if unknown:
            raise ValueError(f"Unknown source(s): {', '.join(unknown)}. Valid: {', '.join(REGISTRY)}")
        allowed_collectors = {REGISTRY[s].name for s in source_keys}

    tickers = sorted({r["ticker"] for r in rows})
    companies = {c["ticker"]: c for c in repo.get_companies(conn, tickers)}
    targets: list[tuple[dict, object]] = []
    for row in rows:
        ticker = row["ticker"]
        collector_name = row["collector_name"]
        if allowed_collectors is not None and collector_name not in allowed_collectors:
            continue
        company = companies.get(ticker)
        collector = COLLECTOR_BY_NAME.get(collector_name or "")
        if company is None or collector is None:
            continue
        targets.append((company, collector))
    return targets


def retry_failed_collection(
    conn: sqlite3.Connection,
    *,
    tickers: list[str] | None = None,
    source_keys: list[str] | None = None,
    statuses: frozenset[str] | None = None,
) -> tuple[list[dict], dict]:
    """Re-run collectors for latest failed (ticker, source) pairs."""
    collector_names = None
    if source_keys:
        collector_names = [REGISTRY[s].name for s in source_keys]
    rows = repo.failed_status_rows(
        conn,
        tickers=tickers,
        collector_names=collector_names,
        statuses=statuses,
    )
    targets = build_retry_targets(conn, rows, source_keys=source_keys)
    if not targets:
        return rows, {"run_id": None, "evidence": 0, "documents": 0, "ok": 0, "failed": 0, "runtime_seconds": 0.0}
    totals = run_targeted_collection(
        conn,
        targets,
        command="retry-failed",
        args={
            "tickers": tickers,
            "sources": source_keys,
            "pairs": len(targets),
        },
    )
    return rows, totals


def format_retry_plan(rows: list[dict]) -> str:
    """Human-readable summary of pairs scheduled for retry."""
    if not rows:
        return "No retryable failures (latest status per ticker×source)."
    lines = [f"{'TICKER':<8} {'COLLECTOR':<18} {'STATUS':<20} DETAIL"]
    for row in rows:
        detail = (row.get("message") or "")[:60]
        lines.append(
            f"{row['ticker']:<8} {row.get('collector_name') or '':<18} "
            f"{row.get('status') or '':<20} {detail}"
        )
    return "\n".join(lines)
