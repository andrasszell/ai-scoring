from __future__ import annotations

import sqlite3

# Lightweight, append-only migration system. Each migration has an integer
# version, a name, and SQL. Applied in order; applied versions are tracked in
# `schema_migrations`. Never edit a released migration — add a new one.

_MIGRATION_0001 = """
CREATE TABLE IF NOT EXISTS companies (
    ticker TEXT PRIMARY KEY,
    company_id TEXT,
    company_name TEXT NOT NULL,
    sector TEXT,
    industry TEXT,
    cik TEXT,
    exchange TEXT,
    country TEXT,
    website_domain TEXT,
    parent_company TEXT,
    source_of_identifier TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS company_aliases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    alias TEXT NOT NULL,
    alias_type TEXT,
    source TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ticker, alias, alias_type),
    FOREIGN KEY(ticker) REFERENCES companies(ticker)
);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT,
    ticker TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_name TEXT,
    source_url TEXT,
    source_date TEXT,
    retrieved_at TEXT DEFAULT CURRENT_TIMESTAMP,
    title TEXT,
    raw_path TEXT,
    text_path TEXT,
    content_hash TEXT,
    parser_version TEXT,
    metadata_json TEXT,
    UNIQUE(ticker, source_type, source_url),
    FOREIGN KEY(ticker) REFERENCES companies(ticker)
);

CREATE TABLE IF NOT EXISTS evidence_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT,
    ticker TEXT NOT NULL,
    company_name TEXT,
    source_type TEXT NOT NULL,
    source_name TEXT,
    source_url TEXT,
    source_date TEXT,
    retrieved_at TEXT DEFAULT CURRENT_TIMESTAMP,
    evidence_text TEXT NOT NULL,
    evidence_title TEXT,
    evidence_context TEXT,
    raw_document_id INTEGER,
    collector_name TEXT NOT NULL,
    collector_version TEXT NOT NULL,
    language TEXT,
    metadata_json TEXT,
    collection_status TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(ticker) REFERENCES companies(ticker),
    FOREIGN KEY(raw_document_id) REFERENCES documents(id)
);

CREATE TABLE IF NOT EXISTS raw_api_responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT,
    source_type TEXT,
    collector_name TEXT,
    collector_version TEXT,
    request_url TEXT,
    request_params TEXT,
    status_code INTEGER,
    response_text TEXT,
    content_hash TEXT,
    retrieved_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS collector_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    command TEXT,
    args_json TEXT,
    started_at TEXT DEFAULT CURRENT_TIMESTAMP,
    finished_at TEXT,
    status TEXT
);

CREATE TABLE IF NOT EXISTS collector_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER,
    ticker TEXT NOT NULL,
    source_type TEXT NOT NULL,
    collector_name TEXT,
    collector_version TEXT,
    status TEXT NOT NULL,
    message TEXT,
    evidence_count INTEGER DEFAULT 0,
    documents_count INTEGER DEFAULT 0,
    api_calls INTEGER DEFAULT 0,
    duration_seconds REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(run_id) REFERENCES collector_runs(id)
);

CREATE TABLE IF NOT EXISTS collection_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER,
    ticker TEXT,
    metric_name TEXT NOT NULL,
    metric_value REAL,
    metric_text TEXT,
    source TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_evidence_ticker ON evidence_items(ticker);
CREATE INDEX IF NOT EXISTS idx_evidence_collector ON evidence_items(ticker, collector_name);
CREATE INDEX IF NOT EXISTS idx_documents_ticker ON documents(ticker);
CREATE INDEX IF NOT EXISTS idx_status_ticker ON collector_status(ticker);
"""

# Coding Standards §4/§6: evidence must carry a raw hash, an initial (source-prior)
# confidence, and a classified source category + reliability.
_MIGRATION_0002 = """
ALTER TABLE evidence_items ADD COLUMN raw_hash TEXT;
ALTER TABLE evidence_items ADD COLUMN confidence_initial REAL;
ALTER TABLE evidence_items ADD COLUMN source_category TEXT;
ALTER TABLE evidence_items ADD COLUMN source_reliability TEXT;
CREATE INDEX IF NOT EXISTS idx_evidence_raw_hash ON evidence_items(raw_hash);
"""

# Coding Standards §4/§5: scores must be persisted with a versioned formula, the
# inputs they were computed from, and an explanation. (Owned by the inference layer,
# but the table lives in the shared DB.)
_MIGRATION_0003 = """
CREATE TABLE IF NOT EXISTS scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    score_type TEXT NOT NULL,
    score_value REAL NOT NULL,
    score_version TEXT,
    formula_version TEXT,
    input_evidence_ids TEXT,
    explanation_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(ticker) REFERENCES companies(ticker)
);
CREATE INDEX IF NOT EXISTS idx_scores_ticker ON scores(ticker);
"""

MIGRATIONS: list[tuple[int, str, str]] = [
    (1, "initial_evidence_schema", _MIGRATION_0001),
    (2, "evidence_source_quality_fields", _MIGRATION_0002),
    (3, "scores_table", _MIGRATION_0003),
]


def _ensure_migrations_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT,
            applied_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()


def current_version(conn: sqlite3.Connection) -> int:
    _ensure_migrations_table(conn)
    row = conn.execute("SELECT MAX(version) AS v FROM schema_migrations").fetchone()
    return int(row["v"]) if row and row["v"] is not None else 0


def apply_migrations(conn: sqlite3.Connection) -> list[int]:
    """Apply any pending migrations in order. Returns the versions applied."""
    _ensure_migrations_table(conn)
    applied = current_version(conn)
    newly: list[int] = []
    for version, name, sql in sorted(MIGRATIONS):
        if version <= applied:
            continue
        conn.executescript(sql)
        conn.execute(
            "INSERT INTO schema_migrations(version, name) VALUES(?, ?)",
            (version, name),
        )
        conn.commit()
        newly.append(version)
    return newly
