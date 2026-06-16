from __future__ import annotations

import csv
import json
from pathlib import Path

# Clean exports for the inference team (Implementation Plan §16). All exports are
# pure reads of the evidence corpus — no scoring, no interpretation.

_EXPORTS = {
    "companies": "SELECT * FROM companies ORDER BY ticker",
    "documents": "SELECT * FROM documents ORDER BY ticker, source_type, source_date",
    "evidence_items": "SELECT * FROM evidence_items ORDER BY ticker, source_type, created_at",
    "collector_status": (
        "SELECT * FROM collector_status WHERE id IN "
        "(SELECT MAX(id) FROM collector_status GROUP BY ticker, source_type) "
        "ORDER BY ticker, source_type"
    ),
}


def _rows(conn, table: str, tickers: list[str] | None) -> list[dict]:
    sql = _EXPORTS[table]
    params: list = []
    if tickers:
        norm = [t.upper().replace(".", "-") for t in tickers]
        # Wrap the base query so the ticker filter works regardless of clauses.
        sql = f"SELECT * FROM ({sql}) WHERE ticker IN ({','.join('?' for _ in norm)})"
        params = norm
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def export_table_csv(conn, table: str, output: str | Path, tickers: list[str] | None = None) -> int:
    rows = _rows(conn, table, tickers)
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else ["ticker"]
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def export_evidence_jsonl(conn, output: str | Path, tickers: list[str] | None = None) -> int:
    """Preferred advanced format: one JSON evidence object per line (§16)."""
    rows = _rows(conn, "evidence_items", tickers)
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for r in rows:
            if r.get("metadata_json"):
                try:
                    r["metadata"] = json.loads(r["metadata_json"])
                except (ValueError, TypeError):
                    r["metadata"] = {}
            f.write(json.dumps(r, default=str) + "\n")
    return len(rows)
