from __future__ import annotations

import json
import sqlite3
from typing import Iterable

from ..logging_config import get_logger
from ..models import CollectorResult
from ..validation import validate_evidence

logger = get_logger("evidence_collection.repository")

# ---------------------------------------------------------------------------
# Companies & aliases
# ---------------------------------------------------------------------------

_COMPANY_FIELDS = (
    "ticker",
    "company_id",
    "company_name",
    "sector",
    "industry",
    "cik",
    "exchange",
    "country",
    "website_domain",
    "parent_company",
    "source_of_identifier",
)


def upsert_companies(conn: sqlite3.Connection, rows: Iterable[dict]) -> int:
    payloads = []
    for r in rows:
        payload = {k: r.get(k) for k in _COMPANY_FIELDS}
        if not payload.get("company_id"):
            payload["company_id"] = payload["ticker"]
        payloads.append(payload)
    if not payloads:
        return 0
    conn.executemany(
        """
        INSERT INTO companies(
            ticker, company_id, company_name, sector, industry, cik,
            exchange, country, website_domain, parent_company, source_of_identifier
        ) VALUES(
            :ticker, :company_id, :company_name, :sector, :industry, :cik,
            :exchange, :country, :website_domain, :parent_company, :source_of_identifier
        )
        ON CONFLICT(ticker) DO UPDATE SET
          company_name=excluded.company_name,
          sector=COALESCE(excluded.sector, companies.sector),
          industry=COALESCE(excluded.industry, companies.industry),
          cik=COALESCE(excluded.cik, companies.cik),
          exchange=COALESCE(excluded.exchange, companies.exchange),
          country=COALESCE(excluded.country, companies.country),
          website_domain=COALESCE(excluded.website_domain, companies.website_domain),
          parent_company=COALESCE(excluded.parent_company, companies.parent_company),
          source_of_identifier=excluded.source_of_identifier,
          updated_at=CURRENT_TIMESTAMP
        """,
        payloads,
    )
    conn.commit()
    return len(payloads)


def get_companies(conn, tickers: list[str] | None = None, limit: int | None = None) -> list[dict]:
    if tickers:
        placeholders = ",".join("?" for _ in tickers)
        rows = conn.execute(
            f"SELECT * FROM companies WHERE ticker IN ({placeholders}) ORDER BY ticker",
            [t.upper().replace(".", "-") for t in tickers],
        ).fetchall()
    else:
        sql = "SELECT * FROM companies ORDER BY ticker"
        if limit:
            sql += f" LIMIT {int(limit)}"
        rows = conn.execute(sql).fetchall()
    return [dict(r) for r in rows]


def count_companies(conn) -> int:
    return int(conn.execute("SELECT COUNT(*) AS n FROM companies").fetchone()["n"])


def insert_alias(conn, ticker: str, alias: str, alias_type: str, source: str | None = None) -> None:
    conn.execute(
        """
        INSERT INTO company_aliases(ticker, alias, alias_type, source)
        VALUES(?, ?, ?, ?)
        ON CONFLICT(ticker, alias, alias_type) DO NOTHING
        """,
        (ticker, alias, alias_type, source),
    )
    conn.commit()


def get_aliases(conn, ticker: str) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM company_aliases WHERE ticker=?", (ticker,))]


# ---------------------------------------------------------------------------
# Documents & raw responses
# ---------------------------------------------------------------------------


def insert_document(conn, doc: dict) -> int:
    fields = (
        "company_id", "ticker", "source_type", "source_name", "source_url",
        "source_date", "title", "raw_path", "text_path", "content_hash",
        "parser_version", "metadata_json",
    )
    payload = {k: doc.get(k) for k in fields}
    # Content-hash dedup: if we already stored identical content for this company
    # under a different URL, reuse it instead of creating a near-duplicate row.
    chash = payload.get("content_hash")
    if chash:
        dup = conn.execute(
            "SELECT id FROM documents WHERE ticker=? AND content_hash=? LIMIT 1",
            (payload["ticker"], chash),
        ).fetchone()
        if dup:
            return int(dup["id"])
    conn.execute(
        """
        INSERT INTO documents(
            company_id, ticker, source_type, source_name, source_url, source_date,
            title, raw_path, text_path, content_hash, parser_version, metadata_json
        ) VALUES(
            :company_id, :ticker, :source_type, :source_name, :source_url, :source_date,
            :title, :raw_path, :text_path, :content_hash, :parser_version, :metadata_json
        )
        ON CONFLICT(ticker, source_type, source_url) DO UPDATE SET
          source_name=excluded.source_name,
          source_date=excluded.source_date,
          title=excluded.title,
          raw_path=excluded.raw_path,
          text_path=excluded.text_path,
          content_hash=excluded.content_hash,
          parser_version=excluded.parser_version,
          metadata_json=excluded.metadata_json,
          retrieved_at=CURRENT_TIMESTAMP
        """,
        payload,
    )
    conn.commit()
    row = conn.execute(
        "SELECT id FROM documents WHERE ticker=? AND source_type=? AND source_url IS ?",
        (payload["ticker"], payload["source_type"], payload["source_url"]),
    ).fetchone()
    return int(row["id"])


def save_raw_response(conn, *, ticker, source_type, collector_name, collector_version,
                      request_url, request_params, status_code, response_text, content_hash) -> int:
    # Dedup identical API responses for the same company/collector.
    if content_hash:
        dup = conn.execute(
            "SELECT id FROM raw_api_responses WHERE ticker=? AND collector_name=? AND content_hash=? LIMIT 1",
            (ticker, collector_name, content_hash),
        ).fetchone()
        if dup:
            return int(dup["id"])
    cur = conn.execute(
        """
        INSERT INTO raw_api_responses(
            ticker, source_type, collector_name, collector_version,
            request_url, request_params, status_code, response_text, content_hash
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (ticker, source_type, collector_name, collector_version,
         request_url, request_params, status_code, response_text, content_hash),
    )
    conn.commit()
    return int(cur.lastrowid)


# ---------------------------------------------------------------------------
# Evidence items
# ---------------------------------------------------------------------------

_EVIDENCE_FIELDS = (
    "company_id", "ticker", "company_name", "source_type", "source_name",
    "source_url", "source_date", "evidence_text", "evidence_title",
    "evidence_context", "raw_document_id", "collector_name", "collector_version",
    "language", "metadata_json", "collection_status",
    "raw_hash", "confidence_initial", "source_category", "source_reliability",
)


def delete_evidence(conn, ticker: str, collector_name: str) -> int:
    """Remove a company's evidence from one collector (idempotent re-runs)."""
    cur = conn.execute(
        "DELETE FROM evidence_items WHERE ticker=? AND collector_name=?",
        (ticker, collector_name),
    )
    conn.commit()
    return cur.rowcount


def _existing_evidence_hashes(conn, pairs: set[tuple[str, str]]) -> set[tuple[str, str, str]]:
    """Existing (ticker, collector_name, raw_hash) tuples for the given pairs."""
    existing: set[tuple[str, str, str]] = set()
    for ticker, collector in pairs:
        for r in conn.execute(
            "SELECT raw_hash FROM evidence_items WHERE ticker=? AND collector_name=? AND raw_hash IS NOT NULL",
            (ticker, collector),
        ):
            existing.add((ticker, collector, r["raw_hash"]))
    return existing


def insert_evidence(conn, rows: Iterable[dict]) -> int:
    """Insert evidence after validation (§22) and deduplication (§13).

    Invalid rows (no source URL/date, missing traceability fields) are dropped and
    logged — never silently stored. Rows duplicating an existing `raw_hash` within
    the same (ticker, collector) are skipped.
    """
    rows = list(rows)
    pairs = {(r.get("ticker"), r.get("collector_name")) for r in rows if r.get("ticker")}
    existing = _existing_evidence_hashes(conn, pairs)
    seen: set[tuple[str, str, str]] = set()
    rejected = 0
    duplicates = 0
    payloads = []
    for r in rows:
        errors = validate_evidence(r)
        if errors:
            rejected += 1
            logger.warning("rejected evidence (%s) for %s/%s: %s",
                           "; ".join(errors), r.get("ticker"), r.get("collector_name"),
                           (r.get("evidence_text") or "")[:60])
            continue
        rh = r.get("raw_hash")
        key = (r.get("ticker"), r.get("collector_name"), rh)
        if rh and (key in seen or key in existing):
            duplicates += 1
            continue
        seen.add(key)
        payload = {k: r.get(k) for k in _EVIDENCE_FIELDS}
        if not payload.get("company_id"):
            payload["company_id"] = payload.get("ticker")
        payloads.append(payload)
    if rejected or duplicates:
        logger.info("evidence insert: %d valid, %d rejected, %d duplicates",
                    len(payloads), rejected, duplicates)
    if not payloads:
        return 0
    conn.executemany(
        """
        INSERT INTO evidence_items(
            company_id, ticker, company_name, source_type, source_name, source_url,
            source_date, evidence_text, evidence_title, evidence_context,
            raw_document_id, collector_name, collector_version, language,
            metadata_json, collection_status,
            raw_hash, confidence_initial, source_category, source_reliability
        ) VALUES(
            :company_id, :ticker, :company_name, :source_type, :source_name, :source_url,
            :source_date, :evidence_text, :evidence_title, :evidence_context,
            :raw_document_id, :collector_name, :collector_version, :language,
            :metadata_json, :collection_status,
            :raw_hash, :confidence_initial, :source_category, :source_reliability
        )
        """,
        payloads,
    )
    conn.commit()
    return len(payloads)


# ---------------------------------------------------------------------------
# Runs, status, operational metrics
# ---------------------------------------------------------------------------


def start_run(conn, command: str, args: dict) -> int:
    cur = conn.execute(
        "INSERT INTO collector_runs(command, args_json, status) VALUES(?, ?, 'running')",
        (command, json.dumps(args, default=str)),
    )
    conn.commit()
    return int(cur.lastrowid)


def finish_run(conn, run_id: int, status: str = "completed") -> None:
    conn.execute(
        "UPDATE collector_runs SET finished_at=CURRENT_TIMESTAMP, status=? WHERE id=?",
        (status, run_id),
    )
    conn.commit()


def record_status(conn, *, run_id, ticker, source_type, collector_name,
                  collector_version, result: CollectorResult, duration_seconds: float) -> None:
    conn.execute(
        """
        INSERT INTO collector_status(
            run_id, ticker, source_type, collector_name, collector_version,
            status, message, evidence_count, documents_count, api_calls, duration_seconds
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (run_id, ticker, source_type, collector_name, collector_version,
         result.status, result.message, result.evidence_count,
         result.documents_count, result.api_calls, duration_seconds),
    )
    conn.commit()


def upsert_collection_metric(conn, *, run_id, ticker, name, value=None, text=None, source=None) -> None:
    conn.execute(
        """
        INSERT INTO collection_metrics(run_id, ticker, metric_name, metric_value, metric_text, source)
        VALUES(?, ?, ?, ?, ?, ?)
        """,
        (run_id, ticker, name, value, text, source),
    )
    conn.commit()


def quality_report(conn) -> dict:
    """Collection-quality / validation report (Coding Standards §14, §18).

    Read-only audit of the evidence corpus. Reports rule violations and coverage.
    """
    def scalar(sql: str) -> int:
        return int(conn.execute(sql).fetchone()[0])

    total = scalar("SELECT COUNT(*) FROM evidence_items")
    missing_anchor = scalar(
        "SELECT COUNT(*) FROM evidence_items "
        "WHERE (source_url IS NULL OR source_url='') AND (source_date IS NULL OR source_date='')"
    )
    missing_hash = scalar("SELECT COUNT(*) FROM evidence_items WHERE raw_hash IS NULL OR raw_hash=''")
    missing_category = scalar("SELECT COUNT(*) FROM evidence_items WHERE source_category IS NULL")
    dup_rows = scalar(
        "SELECT COALESCE(SUM(c-1),0) FROM ("
        "  SELECT COUNT(*) AS c FROM evidence_items WHERE raw_hash IS NOT NULL "
        "  GROUP BY ticker, collector_name, raw_hash HAVING c > 1)"
    )
    coverage = [
        dict(r) for r in conn.execute(
            "SELECT source_type, source_category, source_reliability, COUNT(*) AS rows, "
            "COUNT(DISTINCT ticker) AS companies FROM evidence_items "
            "GROUP BY source_type, source_category, source_reliability ORDER BY source_type"
        )
    ]
    companies_with_evidence = scalar("SELECT COUNT(DISTINCT ticker) FROM evidence_items")
    return {
        "total_evidence": total,
        "companies_with_evidence": companies_with_evidence,
        "violations": {
            "missing_source_anchor": missing_anchor,
            "missing_raw_hash": missing_hash,
            "missing_source_category": missing_category,
            "duplicate_raw_hash_rows": dup_rows,
        },
        "coverage": coverage,
    }


def status_summary(conn, tickers: list[str] | None = None) -> list[dict]:
    """Latest status per (ticker, source_type)."""
    sql = """
        SELECT ticker, source_type, collector_name, collector_version, status, message,
               evidence_count, documents_count, api_calls, created_at
        FROM collector_status s
        WHERE id IN (
            SELECT MAX(id) FROM collector_status GROUP BY ticker, source_type
        )
    """
    params: list = []
    if tickers:
        norm = [t.upper().replace(".", "-") for t in tickers]
        sql += f" AND ticker IN ({','.join('?' for _ in norm)})"
        params = norm
    sql += " ORDER BY ticker, source_type"
    return [dict(r) for r in conn.execute(sql, params)]
