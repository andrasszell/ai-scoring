# Evidence export field definitions

Frozen reference for Team 2 (inference) consuming `ai-collect export-all` or
`ai-collect snapshot` bundles. Schema version tracked in `manifest.json`.

**Snapshot command:** `ai-collect snapshot --output-dir data/exports/snapshots/corpus_YYYYMMDD`

---

## `companies.csv`

| Field | Type | Description |
|---|---|---|
| `ticker` | string | Primary key; normalized (e.g. `BRK-B`) |
| `company_name` | string | Display name |
| `cik` | string | SEC Central Index Key |
| `sector` | string | GICS sector (from Wikipedia load) |
| `industry` | string | GICS industry |
| `website_domain` | string | First-party domain when known |
| `exchange` | string | Listing exchange |
| `country` | string | Country of incorporation |

---

## `documents.csv`

| Field | Type | Description |
|---|---|---|
| `id` | int | Document row id |
| `ticker` | string | Company ticker |
| `source_type` | string | e.g. `sec_annual_filing`, `earnings_call_transcript` |
| `source_url` | string | Canonical source URL or `fmp://` URI |
| `source_date` | string | Document date (ISO or vendor format) |
| `text_path` | string | Path to stored raw text under `data/raw/` |
| `content_hash` | string | SHA-256 of document text |
| `parser_version` | string | Extraction adapter version |

---

## `evidence_items.csv` / `evidence_items.jsonl` / `evidence_items.parquet`

| Field | Type | Description |
|---|---|---|
| `id` | int | Evidence row id |
| `ticker` | string | Company ticker |
| `source_type` | string | Pillar / evidence category |
| `source_category` | string | Coding Standards category (e.g. `regulatory_filing`) |
| `source_reliability` | string | `high` / `medium` / `low` |
| `source_url` | string | Traceability URL (required unless `source_date` set) |
| `source_date` | string | Evidence anchor date |
| `evidence_text` | string | Candidate paragraph text |
| `evidence_title` | string | Optional title |
| `collector_name` | string | Collector that produced this row |
| `collector_version` | string | Semver of collector logic |
| `raw_hash` | string | Content hash for deduplication |
| `confidence_initial` | float | Source-prior confidence (0–1) |
| `raw_document_id` | int | FK to `documents.id` when applicable |
| `metadata_json` | string | Collector-specific JSON (keywords, quarter, etc.) |

JSONL rows may include a parsed `metadata` object.

---

## `collector_status.csv`

Latest status per `(ticker, source_type)` — collection audit trail.

| Field | Type | Description |
|---|---|---|
| `ticker` | string | Company ticker |
| `source_type` | string | Source pillar |
| `collector_name` | string | Collector id |
| `status` | string | `success`, `no_results`, `skipped`, `rate_limited`, etc. |
| `message` | string | Outcome detail; Block F `reason:*` when applicable |
| `evidence_count` | int | Rows inserted this run |
| `documents_count` | int | Documents stored |
| `api_calls` | int | API calls consumed |
| `created_at` | string | Status timestamp (UTC) |

---

## `manifest.json` (snapshots only)

| Field | Description |
|---|---|
| `snapshot_version` | Manifest format version |
| `tag` | Optional label (e.g. `phase3_sp500`) |
| `generated_at` | ISO-8601 UTC |
| `schema_version` | SQLite migration version |
| `latest_collect_run_id` | Most recent `collector_runs.id` |
| `files` | Row counts per export file |
| `validate` | Violation counts from `ai-collect validate` |
| `coverage` | Evidence rows by `source_type` |
| `source_coverage` | Per-pillar tickers with/without evidence (see `ai-collect coverage`) |
| `field_definitions` | Path to this document |

---

## Reproducibility

- Raw documents: `data/raw/` (SEC HTML, earnings text).
- Full DB: copy `data/evidence.sqlite` for exact replay.
- Re-extract without network: `ai-collect reprocess --source sec earnings`.

See [`data-sources.md`](data-sources.md) for platform registry and outcome semantics.
