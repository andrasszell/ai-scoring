# AI Adoption Intelligence Platform

A monorepo with two clearly separated layers:

| Layer | Package | CLI | Owns |
|---|---|---|---|
| **Evidence Discovery (Team 1)** | `evidence_collection` | `ai-collect` | Finding, retrieving, normalizing, and preserving public AI evidence |
| **Inference (Team 2)** | `inference` | `ai-score` | Interpreting evidence and producing the AI Depth Score |

The non-negotiable design rule (see `docs/Implementation Plan for Data Collection Team.md`):
the collection layer **finds and preserves evidence**; it does **not** score
companies or decide what evidence means. Scoring lives entirely in `inference`.

## What the collection layer produces

A versioned, auditable evidence corpus in SQLite:

```
Company Universe  +  Raw Documents  +  Candidate Evidence  +  Source Metadata
+  Collector Status  +  Clean Exports (CSV / JSONL)
```

Every evidence item is traceable to a source URL/date, a stored document, and the
exact collector name+version that produced it.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Edit `.env` and set at least the SEC contact (required by EDGAR fair-access):

```bash
SEC_USER_AGENT="Your Name your.email@example.com"
```

Optional API keys (collectors lacking their key are **skipped gracefully** and
record an `api_key_missing` status — never a silent failure):

```bash
FMP_API_KEY="..."              # earnings-call transcripts (usually a paid plan)
SERPAPI_API_KEY="..."          # product/service + hiring (Google Jobs incl. LinkedIn)
SEMANTIC_SCHOLAR_API_KEY="..." # research papers; optional, raises rate limits
PATENTSVIEW_API_KEY="..."      # AI patent activity (PatentsView Search API)
```

### Which source needs which key

| Source key | Collector | Source | Key required? |
|---|---|---|---|
| `sec` | `sec_filings` | SEC EDGAR (10-K, 20-F, 40-F + amendments) | No (just `SEC_USER_AGENT`) |
| `earnings` | `earnings_calls` | Financial Modeling Prep | `FMP_API_KEY` |
| `products` | `web_products` | Google via SerpAPI | `SERPAPI_API_KEY` |
| `hiring` | `hiring_jobs` | Google Jobs via SerpAPI (incl. LinkedIn) | `SERPAPI_API_KEY` |
| `patents` | `patents` | PatentsView Search API | `PATENTSVIEW_API_KEY` |
| `research` | `research` | Semantic Scholar | Optional (rate-limited without) |

## Collect evidence (`ai-collect`)

```bash
ai-collect init-db                          # create DB + apply migrations
ai-collect load-companies                   # load S&P 500 universe + CIKs
ai-collect collect --ticker MSFT NVDA       # specific companies (all sources)
ai-collect collect --source sec research    # limit to specific sources
ai-collect collect --all                    # every loaded company
ai-collect status                           # latest status per company/source
ai-collect validate                         # audit corpus: rule violations + coverage
ai-collect reprocess --source sec           # re-extract evidence from stored docs (no network)
```

`collect` validates every evidence row on insert (rejects rows with no source URL
or date, §22) and **deduplicates** by content hash. `reprocess` rebuilds evidence
from preserved raw documents, so improved extraction logic can be applied without
re-hitting source APIs.

`collect` with no `--ticker/--limit/--all` runs the default mega-caps
(`DEFAULT_TICKERS` in `config.py`). It auto-loads the universe if the DB is empty.

### Analyze one company by name

```bash
ai-collect analyze Microsoft
ai-collect analyze "Elanco Animal Health"   # falls back to the full SEC filer list
ai-collect analyze NVDA --source sec
```

`analyze` resolves the name (exact → prefix → substring), falls back to all SEC
filers for non-index companies, and lists candidates when a name is ambiguous.

## Export for the inference team

```bash
ai-collect export-all --output-dir data/exports        # companies/documents/evidence/status
ai-collect export-evidence --format jsonl --output data/exports/evidence.jsonl
ai-collect export-evidence --ticker MSFT NVDA          # scope to specific tickers
```

`export-all` writes `companies.csv`, `documents.csv`, `evidence_items.csv`,
`collector_status.csv`, and `evidence_items.jsonl`.

## Score (`ai-score`, inference layer)

Scoring is a **separate** tool that only reads the evidence corpus:

```bash
ai-score score --ticker MSFT NVDA            # prints per-driver explanation
ai-score score --persist                     # also writes versioned rows to scores table
ai-score export-scores --output data/exports/ai_depth_scores.csv
```

The current scorer is the MVP heuristic carried over from the prototype: it counts
evidence items per collector, caps each signal, and produces a weighted 0–100
score. It is **versioned** (`ai_adoption_score_v0_1`), returns a per-driver
**explanation**, records the **input evidence ids**, and persists append-only rows
to the `scores` table. It is expected to be replaced by the mathematical inference
model (which will introduce a `signals` layer — see `docs/implementation-plan.md`).

## Database schema

The collection layer is the single source of truth. Tables (created via the
migration runner in `evidence_collection/db/migrations.py`):

| Table | Purpose |
|---|---|
| `companies` | Universe: ticker, name, sector, industry, CIK, exchange, country, aliases-parent fields |
| `company_aliases` | Brand / legal / former / subsidiary names mapped to a ticker |
| `documents` | One row per source document; raw + text paths, `content_hash`, `parser_version` |
| `evidence_items` | Candidate AI evidence (Evidence Object Standard §8) with collector name+version |
| `raw_api_responses` | Preserved raw API payloads for reproducibility/debugging |
| `collector_runs` | One row per `collect`/`analyze` invocation |
| `collector_status` | Status per (company, source): success / no_results / api_key_missing / … |
| `collection_metrics` | **Operational** metrics only (runtime, counts) — never AI-maturity scores |
| `scores` | Inference output: versioned, explained, append-only AI Depth Scores |
| `schema_migrations` | Applied migration versions |

## Architecture

```
src/
  evidence_collection/        # Team 1 — ai-collect
    cli.py  runner.py  http.py  extraction.py  config.py  logging_config.py
    status.py  models.py  exporters.py
    db/         connection.py  migrations.py  repository.py
    universe/   sp500.py  entity.py
    collectors/ base.py  sec_filings.py  earnings.py  serpapi.py  patents.py  research.py
  inference/                  # Team 2 — ai-score
    scoring.py  cli.py
```

Each collector subclasses `Collector`, declares `name`/`version`/`source_type`,
and returns a `CollectorResult` (status + counts) instead of raising — a single
source failure is recorded as status and never aborts a run.

## Development

```bash
pip install -e ".[dev]"
pytest
```

CI runs the tests on Python 3.10–3.12 via GitHub Actions.

## Roadmap (per the Implementation Plan)

- **Phase 0 (done):** separate collection from scoring; standardize evidence +
  document schema; add collector runs/status, raw-response preservation, clean exports.
- **Phase 1:** stabilize the 6 core collectors; validate 25–50 companies.
- **Phase 2:** high-value sources (technical blogs, docs, GitHub, press, case studies).
- **Phase 3:** scale to the full S&P 500 with refresh + freshness monitoring.
- **Phase 4:** versioned evidence snapshots + field-definition docs for the inference team.
