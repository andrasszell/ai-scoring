from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .collectors import REGISTRY
from .db import repository as repo

SUCCESS_STATUSES = frozenset({"success", "no_results", "skipped"})


def expected_source_types() -> list[str]:
    """Source types for all registered collectors (pillar order)."""
    seen: set[str] = set()
    out: list[str] = []
    for collector in REGISTRY.values():
        if collector.source_type not in seen:
            seen.add(collector.source_type)
            out.append(collector.source_type)
    return out


def build_coverage_report(
    conn: sqlite3.Connection,
    companies: list[dict],
) -> dict:
    """Per-pillar evidence coverage and gap list for S&P-scale reporting."""
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    tickers = [c["ticker"] for c in companies]
    source_types = expected_source_types()

    evidence_counts: dict[tuple[str, str], int] = {}
    sql = """
        SELECT ticker, source_type, COUNT(*) AS evidence_count
        FROM evidence_items
    """
    params: list = []
    if tickers:
        norm = [t.upper().replace(".", "-") for t in tickers]
        sql += f" WHERE ticker IN ({','.join('?' for _ in norm)})"
        params = norm
    sql += " GROUP BY ticker, source_type"
    for row in conn.execute(sql, params).fetchall():
        evidence_counts[(row["ticker"], row["source_type"])] = int(row["evidence_count"])

    statuses = repo.status_summary(conn, tickers or None)
    status_by_pair = {(r["ticker"], r["source_type"]): r for r in statuses}

    by_source: dict[str, dict] = {}
    gaps: list[dict] = []

    for source_type in source_types:
        with_evidence: list[str] = []
        without_evidence: list[str] = []
        for company in companies:
            ticker = company["ticker"]
            count = evidence_counts.get((ticker, source_type), 0)
            status_row = status_by_pair.get((ticker, source_type))
            if count > 0:
                with_evidence.append(ticker)
            else:
                without_evidence.append(ticker)
                gaps.append(
                    {
                        "ticker": ticker,
                        "source_type": source_type,
                        "evidence_count": 0,
                        "last_status": status_row.get("status") if status_row else None,
                        "collector_name": status_row.get("collector_name") if status_row else None,
                        "last_collected_at": status_row.get("created_at") if status_row else None,
                    }
                )
        by_source[source_type] = {
            "with_evidence": len(with_evidence),
            "without_evidence": len(without_evidence),
            "missing_tickers": without_evidence,
        }

    return {
        "generated_at": generated_at,
        "companies_total": len(companies),
        "source_types": source_types,
        "summary": by_source,
        "gaps": gaps,
    }


def format_coverage_report(
    report: dict,
    *,
    missing_only: bool = False,
    max_tickers: int = 15,
) -> str:
    lines = [
        f"Coverage report ({report['generated_at']}, {report['companies_total']} companies)",
        "",
        f"  {'SOURCE':<26} {'WITH':>6} {'WITHOUT':>8}  SAMPLE_MISSING",
    ]
    for source_type in report["source_types"]:
        row = report["summary"][source_type]
        if missing_only and row["without_evidence"] == 0:
            continue
        sample = ", ".join(row["missing_tickers"][:max_tickers])
        if row["without_evidence"] > max_tickers:
            sample += f", … (+{row['without_evidence'] - max_tickers})"
        if not sample:
            sample = "—"
        lines.append(
            f"  {source_type:<26} {row['with_evidence']:>6} {row['without_evidence']:>8}  {sample}"
        )
    if missing_only and len(lines) == 2:
        lines.append("  (no gaps — all companies have evidence for every source)")
    return "\n".join(lines)


def write_coverage_report(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
