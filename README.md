# AI Adoption Intelligence Platform

A monorepo with two clearly separated layers:

| Layer | Package | CLI | Owns |
|---|---|---|---|
| **Evidence Discovery (Team 1)** | `evidence_collection` | `ai-collect` | Finding, retrieving, normalizing, and preserving public AI evidence |
| **Inference (Team 2)** | `inference` | `ai-score` | Interpreting evidence and producing the AI Depth Score |

The non-negotiable design rule (see `docs/data-collection-initial-plan.md`, especially §6A):
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

Optional API keys — approved platforms live in
[`config/platforms.yaml`](config/platforms.yaml) (source of truth). Operational
detail: [`docs/data-sources.md`](docs/data-sources.md). Inspect runtime key status:

```bash
ai-collect show-platforms          # phase 1 enabled platforms
ai-collect show-platforms --all    # include disabled phase 2/3 stubs
```

Collectors lacking a required key are **skipped gracefully** and record an
`api_key_missing` status — never a silent failure.

```bash
FMP_API_KEY="..."              # earnings-call transcripts (usually a paid plan)
SERPAPI_API_KEY="..."          # product/service + hiring (Google Jobs incl. LinkedIn)
SEMANTIC_SCHOLAR_API_KEY="..." # research papers; optional, raises rate limits
PATENTSVIEW_API_KEY="..."      # AI patent activity (PatentsView Search API)
GITHUB_TOKEN="..."             # GitHub repos; optional, raises rate limits
```

### Which source needs which key

See [`docs/data-sources.md`](docs/data-sources.md) for the full platform table (synced
from the registry). Quick check: `ai-collect show-platforms`.

Company domains and search aliases:
[`config/company_domains.yaml`](config/company_domains.yaml),
[`config/company_aliases.yaml`](config/company_aliases.yaml).
Inspect one company: `ai-collect validate-company MSFT`.

## Collect evidence (`ai-collect`)

```bash
ai-collect init-db                          # create DB + apply migrations
ai-collect load-companies                   # load S&P 500 universe + CIKs + domains/aliases
ai-collect load-companies --validation-set  # also ensure Phase 1 validation tickers (SEC fallback)
ai-collect validate-company MSFT            # inspect identity, aliases, collection status
ai-collect collect --ticker MSFT NVDA       # specific companies (all sources)
ai-collect collect --validation-set         # Phase 1 sample (35 tickers from config)
ai-collect collect --source sec research github press product_docs    # limit sources
ai-collect reprocess --source product_docs --ticker MSFT              # offline re-extract
ai-collect collect --all                    # every loaded company
ai-collect status                           # latest status per company/source
ai-collect show-platforms                   # registry + API key status (no DB)
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
ai-collect resolve "Elanco Animal Health"   # identity only, no collection
```

`analyze` resolves the name (exact → prefix → substring), falls back to all SEC
filers for non-index companies, and lists candidates when a name is ambiguous.

**Score that company:**

```bash
ai-score score --company "Microsoft" --persist   # resolve + score existing evidence
ai-score run --company "Microsoft" --persist     # collect if needed, then score
ai-collect collect --ticker ELAN MSFT            # unknown tickers upserted from SEC
```

Full workflow: [`docs/phase-2-implementation.md`](docs/phase-2-implementation.md) (§ Block 2.0).

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
ai-score score --company "Microsoft"         # resolve by name, then score
ai-score run --company "Elanco Animal Health" --persist
ai-score export-scores --output data/exports/ai_depth_scores.csv
```

`run` collects evidence when none exists (or pass `--collect` to refresh). Companies
outside the S&P 500 load are resolved via SEC filers. See
[`docs/phase-2-implementation.md`](docs/phase-2-implementation.md).

The current scorer is the MVP heuristic carried over from the prototype: it counts
evidence items per collector, caps each signal, and produces a weighted 0–100
score. It is **versioned** (`ai_adoption_score_v0_5`, nine pillars), returns a per-driver
**explanation**, records the **input evidence ids**, and persists append-only rows
to the `scores` table. It is expected to be replaced by the mathematical inference
model (which will introduce a `signals` layer — see [`docs/implementation-plan.md`](docs/implementation-plan.md)).

**Docs:** [`docs/README.md`](docs/README.md) · [`docs/project-control.md`](docs/project-control.md)

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
    status.py  models.py  exporters.py  platforms.py  registry_gate.py
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

## Roadmap (per the initial plan + current status)

- **Phase 0 (done):** separate collection from scoring; standardize evidence +
  document schema; add collector runs/status, raw-response preservation, clean exports.
- **Phase 1 (done):** platform registry, entity metadata, collector stabilization,
  35-company validation sample (`collect --validation-set`). See
  [`docs/phase-1-development-plan.md`](docs/phase-1-development-plan.md).
- **Phase 2 (done):** on-demand scoring, GitHub, press releases, product documentation —
  [`docs/phase-2-implementation.md`](docs/phase-2-implementation.md).
- **Phase 3 (next):** full S&P 500 scale, API-cost tracking, incremental refresh —
  [`docs/phase-3-development-plan.md`](docs/phase-3-development-plan.md).
- **Phase 4:** versioned evidence snapshots + field-definition docs for the inference team.
