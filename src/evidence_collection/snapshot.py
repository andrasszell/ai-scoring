from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .db.migrations import current_version
from .db import repository as repo
from .coverage_report import build_coverage_report
from .exporters import export_evidence_jsonl, export_table_csv


def default_snapshot_dir(tag: str | None = None) -> Path:
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    name = f"corpus_{tag}" if tag else f"corpus_{date_part}"
    return Path("data/exports/snapshots") / name


def create_snapshot(
    conn: sqlite3.Connection,
    output_dir: str | Path,
    *,
    tag: str | None = None,
    tickers: list[str] | None = None,
    companies: list[dict] | None = None,
) -> dict:
    """Export a versioned evidence bundle with manifest for Team 2 handoff."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    counts = {
        "companies.csv": export_table_csv(conn, "companies", out / "companies.csv", tickers),
        "documents.csv": export_table_csv(conn, "documents", out / "documents.csv", tickers),
        "evidence_items.csv": export_table_csv(conn, "evidence_items", out / "evidence_items.csv", tickers),
        "collector_status.csv": export_table_csv(conn, "collector_status", out / "collector_status.csv", tickers),
        "evidence_items.jsonl": export_evidence_jsonl(conn, out / "evidence_items.jsonl", tickers),
    }

    report = repo.quality_report(conn)
    run_id = repo.latest_run_id(conn)
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    company_rows = companies if companies is not None else repo.get_companies(conn, tickers)
    source_coverage = build_coverage_report(conn, company_rows)

    manifest = {
        "snapshot_version": "1",
        "tag": tag,
        "generated_at": generated_at,
        "schema_version": current_version(conn),
        "latest_collect_run_id": run_id,
        "files": counts,
        "validate": {
            "total_evidence": report["total_evidence"],
            "companies_with_evidence": report["companies_with_evidence"],
            "violations": report["violations"],
        },
        "coverage": report["coverage"],
        "source_coverage": source_coverage["summary"],
        "field_definitions": "docs/evidence-field-definitions.md",
    }
    manifest_path = out / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    return {"output_dir": str(out), "manifest": manifest, "counts": counts}
