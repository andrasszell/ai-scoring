# Data Collection — Initial Implementation Plan

## AI Adoption Intelligence Platform — Evidence Discovery Layer

> **Document role:** This is the original strategic plan for Team 1 (Evidence
> Discovery Layer): mission, architecture, standards, and phased roadmap. For
> **current progress** (what is done vs next), see
> [`implementation-plan.md`](implementation-plan.md).

---

## 1. Mission of the Data Collection Team

The data collection team is responsible for building and maintaining the **Evidence Discovery Layer** of the AI Adoption Intelligence Platform.

The purpose of this layer is to find, retrieve, normalize, and preserve public evidence related to how companies use, build, sell, or discuss artificial intelligence.

This team does **not** assign final AI scores.

This team does **not** decide whether a company is deeply AI-enabled.

This team produces a structured, auditable evidence corpus that the mathematical inference team can process.

---

## 2. Core Principle

The data collection layer should optimize for:

```text
coverage
traceability
freshness
source quality
reproducibility
auditability
```

It should not optimize for final score accuracy directly.

The key separation is:

```text
Data Collection Team:
Find and preserve evidence.

Mathematical Processing Team:
Interpret evidence and infer AI depth.
```

This separation prevents the system from confusing evidence volume with actual AI maturity.

---

## 3. Recommendation: Continue Existing Project with Refactor

The existing Python project should be continued, but refactored into a dedicated data collection service.

The current project already supports several important capabilities:

* company universe loading
* SEC filing collection
* earnings-call evidence
* product/service evidence
* hiring evidence
* patent evidence
* research-paper evidence
* SQLite storage
* evidence export
* score export

However, the current project combines collection and scoring. The next version should separate those responsibilities.

### Decision

```text
Continue the existing project as the foundation.
Refactor it into a clean Evidence Discovery Layer.
Move scoring and inference into a separate downstream project or module.
```

### Why not start from zero?

Starting from zero would lose working collector logic, database design, CLI structure, and source integrations.

### Why not keep it unchanged?

The current project still contains placeholder scoring logic. For the new architecture, scoring should not belong to the data collection team.

---

## 4. Target Architecture

The data collection system should produce a clean evidence corpus.

```text
Company Universe
    ↓
Source Connectors
    ↓
Raw Document Collection
    ↓
Text Extraction
    ↓
Candidate Evidence Detection
    ↓
Metadata Normalization
    ↓
Evidence Store
    ↓
Export / API for Inference Team
```

The output should be structured evidence, not final intelligence.

---

## 5. Scope of the Data Collection Team

### In scope

The data collection team owns:

* company universe management
* company identifier resolution
* source connector development
* raw document retrieval
* document parsing
* candidate AI evidence extraction
* evidence metadata normalization
* source freshness tracking
* collection status tracking
* deduplication at document/source level
* export formats for the inference team
* logging, retries, and error handling
* compliance with API rate limits and source terms

### Out of scope

The data collection team does not own:

* final AI score
* latent AI-state model
* Bayesian estimation
* uncertainty model
* sector-normalized scoring
* final maturity classification
* investment interpretation
* mathematical weighting
* source credibility modeling beyond storing source metadata

---

## 6. Data Collection Sources

The data collection layer should support source families in phases.

### Phase 1 — Existing MVP Sources

These are already partially supported and should be stabilized first.
**Approved platforms for each source:** see **§6A.1**.

```text
SEC filings / annual reports
earnings-call transcripts
company product and service evidence
job postings
patents
research papers
```

### Phase 2 — High-Value Expansion Sources

After the core collectors are stable, add:

```text
product documentation
developer documentation
technical blogs
press releases
case studies
GitHub repositories
AI governance documents
cloud marketplace listings
partner announcements
conference talks
```

### Phase 3 — Premium or Licensed Sources

Later, evaluate:

```text
Lightcast
Revelio
Coresignal
Proxycurl
LinkedIn Talent Insights
AlphaSense
FactSet
PitchBook
CB Insights
Similarweb
BuiltWith
```

These sources should be added only if they materially improve evidence quality.

---

## 6A. Data Platform Decisions

This section describes **which platforms** the collection layer uses: external data
providers, internal storage, and the handoff to Team 2.

**Authoritative registry:** platform metadata lives in
[`config/platforms.yaml`](../config/platforms.yaml), loaded at runtime (live since
Phase 1 Step 1.8). See **§6A.4** for schema and change workflow. Tables below are
a human-readable summary; **edit the YAML** to change approved platforms, then sync
[`data-sources.md`](data-sources.md).

### 6A.1 Evidence source platforms (Phase 1 — approved)

Phase 1 stabilizes the six evidence collectors **plus** the company universe
loaders. Each row names the **approved platform/API** for that source in the
current codebase (`ai-collect`).

#### Company universe (prerequisite — not an evidence pillar)

| Purpose | Platform / API | Auth | Cost model | Notes |
|---|---|---|---|---|
| S&P 500 constituents | [Wikipedia — List of S&P 500 companies](https://en.wikipedia.org/wiki/List_of_S%26P_500_companies) | None (descriptive User-Agent) | Free | Sector/industry metadata |
| CIK mapping + SEC fallback universe | [SEC `company_tickers.json`](https://www.sec.gov/files/company_tickers.json) | `SEC_USER_AGENT` (contact string) | Free | Required for EDGAR; also used when a company is not in the S&P 500 list |

CLI: `ai-collect load-companies` (Wikipedia + SEC CIK merge).

#### Phase 1 evidence collectors (approved)

| Pillar | Collector | Platform / API | Env key | Cost / limits | Status |
|---|---|---|---|---|---|
| Annual filings | `sec_filings` | **SEC EDGAR** — submissions JSON + archive HTML | `SEC_USER_AGENT` | Free; ~4 req/s conservative rate limit | **Active** — no paid key |
| Earnings calls | `earnings_calls` | **Financial Modeling Prep** — transcript API | `FMP_API_KEY` | Paid plan typically required for transcripts | **Active** — skipped if key missing |
| Products / services | `web_products` | **SerpAPI** — Google web search | `SERPAPI_API_KEY` | Per-search billing; quota per plan | **Active** — skipped if key missing |
| Hiring | `hiring_jobs` | **SerpAPI** — Google Jobs (incl. LinkedIn listings) | `SERPAPI_API_KEY` | Same SerpAPI account | **Active** — skipped if key missing |
| Patents | `patents` | **PatentsView Search API** | `PATENTSVIEW_API_KEY` | Free key; rate limits apply | **Active** — skipped if key missing |
| Research papers | `research` | **Semantic Scholar** Graph API | `SEMANTIC_SCHOLAR_API_KEY` (optional) | Free tier heavily rate-limited; key raises limits | **Active** — works without key |

**Phase 1 rule:** no new paid vendor is approved until Phase 1 validation (25–50
companies) is complete and gaps are documented. Swapping or adding a platform
follows the **§6A.4 change workflow** (registry entry + collector + tests + docs).

#### Phase 2 sources (planned — registered, disabled)

Stubs in [`config/platforms.yaml`](../config/platforms.yaml): `github_repos`,
`press_releases`, `product_documentation` (`enabled: false`, `phase: 2`). Collectors
not implemented — adding a vendor follows the **§6A.4 change workflow**.

#### Phase 3 premium vendors (evaluate — registered, disabled)

Stubs in the registry: `lightcast`, `alphasense`, `revelio` (`enabled: false`,
`phase: 3`). Additional candidates from §6 Phase 3 (Coresignal, Proxycurl, LinkedIn
Talent Insights, FactSet, PitchBook, CB Insights, Similarweb, BuiltWith) are listed
in [`data-sources.md`](data-sources.md) but not yet in YAML.

**Evaluation criteria** (all must be documented before approval):

```text
Does it materially improve evidence quality vs Phase 1 APIs?
Is legal/licensing use clear for our deployment model?
Cost at S&P 500 scale (and refresh frequency)?
API stability, rate limits, and historical coverage?
Can we store raw responses for audit/reprocess (§9)?
Overlap with an existing approved platform?
```

---

### 6A.2 Storage and artifacts (MVP → scale)

#### Current stack (Phase 0–1 — approved)

| Layer | Platform | Location / config | Role |
|---|---|---|---|
| Structured corpus | **SQLite** (WAL mode) | `AI_DEPTH_DB` → `data/evidence.sqlite` | Companies, documents, evidence, collector status, raw API responses, scores (inference) |
| Schema evolution | In-repo **migration runner** | `evidence_collection/db/migrations.py` | Versioned, append-only migrations |
| Raw documents | **Local filesystem** | `AI_DEPTH_RAW_DIR` → `data/raw/` | SEC filing HTML/text, earnings transcript text |
| Exports | **Local filesystem** | `AI_DEPTH_EXPORT_DIR` → `data/exports/` | CSV + JSONL handoff artifacts |
| Orchestration | **CLI** (`ai-collect`) | Manual or cron | No scheduler framework in Phase 1 |
| Runtime | **Python 3.10+** | `pip install -e .` | Collectors, validation, reprocess |

#### Scale triggers (when to revisit)

| Trigger | Likely upgrade | Owner |
|---|---|---|
| Concurrent writers / multi-user access | **PostgreSQL** (or similar) replacing SQLite | Team 1 pipeline |
| Raw corpus > local disk / need shared access | **Object storage** (S3, GCS, Azure Blob) for `raw/` + manifest in DB | Team 1 pipeline |
| Team 2 analytics at scale | **Parquet** snapshots + optional warehouse (BigQuery, Snowflake, Databricks) | Joint |
| Full S&P 500 scheduled refresh | Job scheduler (**Prefect**, **Airflow**, or cloud cron) + retry queue | Team 1 pipeline |
| Inference team needs live queries | Read-only **REST API** over evidence corpus | Team 1 → Team 2 handoff |

**Phase 1 decision:** stay on SQLite + local files. Do not add Postgres, object
storage, or a scheduler until one of the triggers above is hit during the 25–50
company validation or S&P 500 pilot.

---

### 6A.3 Handoff and exports (Team 1 → Team 2)

Team 2 consumes a **versioned evidence corpus**, not live source APIs.

#### Implemented today (Phase 0–1)

| Format | Command | Use |
|---|---|---|
| `companies.csv` | `ai-collect export-all` | Company universe |
| `documents.csv` | `ai-collect export-all` | Document manifest (paths, hashes) |
| `evidence_items.csv` | `ai-collect export-all` / `export-evidence` | Candidate evidence rows |
| `collector_status.csv` | `ai-collect export-all` | Per-source success/failure audit |
| `evidence_items.jsonl` | `ai-collect export-all` / `export-evidence --format jsonl` | Preferred machine-readable export |
| SQLite file copy | Copy `data/evidence.sqlite` | Full reproducible snapshot |

Team 2 CLI (`ai-score`) reads the shared SQLite DB or exports; it does **not**
call SEC, SerpAPI, or other source APIs.

#### Planned (Phase 4)

```text
Versioned, dated snapshot bundles (corpus vYYYY-MM-DD/)
Parquet export for analytics
Field-definition document frozen per snapshot
Read-only HTTP API (optional)
```

#### Reprocess contract

`ai-collect reprocess` rebuilds evidence from **stored document text** with no
network — this is the reproducibility guarantee (§9). Any new storage backend
must preserve raw documents or raw API responses with content hashes.

---

### 6A.4 Platform registry (single source of truth)

As the number of sources grows, platform metadata must not be scattered across
markdown tables, hardcoded dicts, and collector files. **One registry file** holds
every approved platform; code and docs read from it.

#### Registry file

```text
config/platforms.yaml          ← edit this to add/change platforms
```

Human-readable, version-controlled, reviewable in PRs. No code change required to
approve a platform — only to wire a new collector adapter.

#### Entry schema (each platform)

```yaml
platforms:
  - id: sec_edgar                    # stable identifier (never rename once live)
    collector: sec_filings           # maps to Collector.name in code
    source_type: sec_annual_filing   # evidence_items.source_type
    display_name: SEC EDGAR
    vendor: U.S. Securities and Exchange Commission
    api_base_url: https://data.sec.gov
    auth:
      env_key: SEC_USER_AGENT        # empty = no key required
      required: true
    phase: 1                         # 1 = approved, 2 = planned, 3 = evaluate
    enabled: true                    # false = skip without deleting entry
    cost_model: free
    rate_limit_notes: "~4 req/s conservative"
    source_category: regulatory_filing
    source_reliability: high
    confidence_initial: 0.75
    reprocessable: true              # has stored document text for offline reprocess
    notes: Annual filings (10-K, 20-F, 40-F + amendments)
```

Universe loaders (Wikipedia, SEC tickers) use the same file under a `loaders:` key
with the same fields where applicable.

#### What reads the registry

| Consumer | Uses registry for |
|---|---|
| `evidence_collection.platforms` (loader module) | Parse, validate schema, expose typed `Platform` objects |
| `sources.py` | Default category/reliability/confidence (overridden by registry) |
| Collector registry | Which collectors are enabled; env-key presence checks |
| `ai-collect show-platforms` | Human/ops view of approved platforms and key status |
| `ai-collect collect` | Skip disabled platforms; surface `api_key_missing` from registry |
| `data-sources.md` | **Generated or manually synced** from registry — not independently edited |

#### Adding or changing a platform (change workflow)

Every platform change follows the same steps so it stays simple and reliable:

```text
1. Edit config/platforms.yaml
      — add row, set phase/enabled, fill auth + reliability fields
2. Implement or update collector adapter (if new source)
      — thin adapter: fetch + normalize; no hardcoded vendor metadata
3. Add tests
      — registry schema validation, collector with mocked API, status on missing key
4. Sync docs
      — regenerate or update data-sources.md from registry; note in change-log.md
5. Verify
      — ai-collect show-platforms
      — ai-collect collect --source <new> --ticker <sample>
      — ai-collect validate
```

**Do not** add platform details only to markdown or only to Python constants.
The registry is the approval record; code implements behavior.

#### Phase 3 premium vendors in the registry

Premium candidates (Lightcast, Revelio, etc.) are stored with `phase: 3`,
`enabled: false` until evaluation passes §6A.1 criteria. This keeps the full
vendor landscape visible without activating collectors.

#### Reliability rules

- Registry entries for `phase: 1` with `enabled: true` are **approved for production collection**.
- `phase: 2` entries document intent; collectors must not run until promoted to phase 1.
- Disabling a platform (`enabled: false`) preserves history and config; collectors skip it cleanly.

---

## 7. Company Universe and Entity Resolution

The first responsibility of the collection layer is to know which company is being analyzed.

### Required fields

```text
ticker
company_name
sector
industry
CIK
exchange
country
website_domain
known_aliases
subsidiaries
parent_company
source_of_identifier
```

### Entity resolution requirements

The system must handle:

* ticker lookup
* company-name lookup
* CIK lookup
* subsidiaries
* brand names
* mergers and name changes
* dual listings
* multiple share classes
* foreign issuers
* common ambiguous names

### Example problem

Alphabet may refer to Class A or Class C shares.

The system should preserve company identity clearly and avoid mixing evidence across related but distinct entities.

---

## 8. Evidence Object Standard

Every collected evidence item should follow a common schema.

### Evidence item

```json
{
  "company_id": "",
  "ticker": "",
  "company_name": "",
  "source_type": "",
  "source_name": "",
  "source_url": "",
  "source_date": "",
  "retrieved_at": "",
  "evidence_text": "",
  "evidence_title": "",
  "evidence_context": "",
  "raw_document_id": "",
  "collector_name": "",
  "collector_version": "",
  "language": "",
  "metadata": {},
  "collection_status": ""
}
```

### Important principle

The evidence item should not contain final intelligence judgment.

It may contain source metadata and candidate evidence text, but the inference layer will decide what the evidence means.

---

## 9. Raw Document Standard

Raw documents should be stored separately from extracted evidence.

### Document object

```json
{
  "document_id": "",
  "company_id": "",
  "source_type": "",
  "source_name": "",
  "source_url": "",
  "source_date": "",
  "retrieved_at": "",
  "title": "",
  "raw_path": "",
  "text_path": "",
  "content_hash": "",
  "parser_version": "",
  "metadata": {}
}
```

### Why this matters

Raw document storage allows:

* reprocessing with improved extraction logic
* auditability
* reproducibility
* debugging
* model comparison
* evidence traceability

---

## 10. Candidate Evidence Detection

The collection layer should identify candidate AI-related text, but it should not deeply interpret it.

### Detection methods

Use a combination of:

```text
keyword retrieval
semantic search
section-based retrieval
source-specific extraction rules
metadata filters
document structure analysis
```

### Keyword retrieval

Useful for high recall, but not sufficient for scoring.

Candidate terms may include:

```text
artificial intelligence
AI
machine learning
deep learning
generative AI
large language model
LLM
agent
automation
computer vision
natural language processing
recommendation engine
predictive model
MLOps
AI assistant
copilot
neural network
foundation model
```

### Important rule

Keyword hits should create candidate evidence, not scores.

---

## 11. Metadata Quality Requirements

For every evidence item, the system should capture:

```text
source type
source URL
source date
retrieval date
collector version
company identifier
document identifier
paragraph location
section title if available
content hash
language
API response metadata
```

Metadata quality is critical because the inference team will need to evaluate:

```text
recency
source credibility
source independence
duplication
evidence freshness
sector context
```

---

## 12. Collection Status and Failure Handling

Every collector should produce a status result.

### Status examples

```text
success
no_results
api_key_missing
api_limit_reached
source_unavailable
parse_failed
company_not_found
ambiguous_company
rate_limited
skipped
```

### Why this matters

Absence of evidence is not the same as evidence of absence.

The inference team needs to know whether no evidence was found because:

* the company has no evidence
* the collector failed
* the source was unavailable
* the API key was missing
* the company identifier was ambiguous

---

## 13. Deduplication Responsibilities

The data collection team should handle basic deduplication.

### Collection-layer deduplication

The team should deduplicate:

```text
identical URLs
identical documents
identical text snippets
repeated API results
same job posting from same source
same patent record
same research paper
```

### Not owned by collection team

The collection team does not need to perform deep semantic claim deduplication.

For example, if 20 articles discuss the same AI product launch using different language, the mathematical processing team can cluster those claims later.

---

## 14. Storage Design

> **Platform decisions:** see **§6A.2** for the approved MVP stack (SQLite +
> local files) and scale triggers. This section describes the logical schema only.

SQLite is the approved structured store for Phase 0–1.

Recommended tables:

```text
companies
company_aliases
documents
evidence_items
collector_runs
collector_status
source_records
raw_api_responses
```

### Existing tables to preserve or adapt

The codebase implements (Phase 0 refactor):

```text
companies
company_aliases
documents
evidence_items
collector_runs
collector_status
collection_metrics
raw_api_responses
schema_migrations
```

Legacy prototype tables (`ai_evidence`, `metrics`) were replaced by the above.
The `scores` table is owned by the inference layer but lives in the same DB file
for MVP convenience.

---

## 15. Collection Metrics

The collection team should track operational metrics, not AI maturity metrics.

### Examples

```text
documents_collected_count
evidence_items_collected_count
sources_successful_count
sources_failed_count
latest_source_date
oldest_source_date
collection_runtime_seconds
api_calls_used
parse_failure_count
duplicate_documents_removed
```

These metrics help measure collection quality and coverage.

They should not be used directly as final AI-depth scores.

---

## 16. Output Interface for Mathematical Team

> **Platform decisions:** see **§6A.3** for implemented vs planned export formats
> and the Team 1 → Team 2 handoff contract.

The data collection team should provide clean exports for the processing team.

### Required exports

```text
companies.csv
documents.csv
evidence_items.csv
collector_status.csv
raw_document_manifest.csv
```

### Preferred advanced format

Planned in Phase 4 (see §6A.3):

```text
JSONL evidence export          ← implemented (Phase 0)
SQLite database snapshot       ← implemented (copy DB file)
Parquet export                 ← planned
API endpoint                   ← planned
```

### Evidence export should include

```text
company identifiers
source identifiers
evidence text
source metadata
document metadata
retrieval metadata
collector metadata
```

---

## 17. API and CLI Requirements

The collection team should maintain a clear command-line interface.

### Required commands

```bash
ai-collect init-db
ai-collect load-companies
ai-collect collect --ticker MSFT
ai-collect collect --all
ai-collect collect --source sec
ai-collect collect --source hiring
ai-collect export-evidence
ai-collect export-documents
ai-collect status
```

### Nice-to-have commands

```bash
ai-collect refresh --ticker MSFT
ai-collect validate-company MSFT
ai-collect show-sources MSFT
ai-collect inspect-evidence MSFT
ai-collect backfill --source patents
```

---

## 18. Engineering Quality Requirements

The data collection system should include:

```text
unit tests
integration tests
mock API responses
rate-limit handling
retry logic
structured logging
collector versioning
configuration through environment variables
source-specific adapters
schema migrations
data validation
CI checks
```

Each collector should be independently testable.

---

## 19. Team Roles

### Data Source Engineer

Builds and maintains source connectors.

### Data Pipeline Engineer

Owns storage, exports, scheduling, retries, and validation.

### Entity Resolution Engineer

Maintains company identity, aliases, subsidiaries, and source mapping.

### QA / Data Auditor

Reviews samples of collected evidence and validates source accuracy.

### Technical Lead

Ensures architecture discipline and clean handoff to the mathematical team.

---

## 20. Phase Plan

### Phase 0 — Refactor Existing Project

Goal: separate collection from scoring.

Tasks:

```text
rename project or module around evidence collection
remove final scoring from core collector workflow
keep existing collectors
standardize evidence schema
standardize document schema
add collector run logs
add status reporting
clean exports for inference team
```

Deliverable:

```text
working Evidence Discovery Layer using existing sources
```

---

### Phase 1 — Stabilize Core Collectors

Goal: make current collectors reliable and auditable.

Sources:

```text
SEC filings
earnings calls
product/service search
hiring search
patents
research papers
```

Tasks:

```text
implement platform registry (config/platforms.yaml) — §6A.4
migrate Phase 1 platform metadata from code/docs into registry
add ai-collect show-platforms command
improve error handling
add collector status                    ← done (Phase 0)
add source dates
store raw documents or raw API responses ← done (Phase 0)
deduplicate exact records               ← done (audit remediation)
add tests
validate sample companies (25–50)
populate companies.website_domain
seed company_aliases
```

Deliverable:

```text
high-quality evidence corpus for 25–50 companies
+ platform registry as the single editable source list
```

---

### Phase 2 — Expand High-Value Sources

Goal: add sources that better reveal actual AI depth.

New sources:

```text
technical blogs
product documentation
developer documentation
GitHub
press releases
case studies
AI governance pages
cloud marketplace listings
```

Deliverable:

```text
multi-source evidence corpus for 100 companies
```

---

### Phase 3 — Scale to Full Company Universe

Goal: scale collection to S&P 500 and beyond.

Tasks:

```text
run collection for full S&P 500
track API costs
handle rate limits
add incremental refresh
add data freshness monitoring
add failed-source retry queue
```

Deliverable:

```text
refreshable S&P 500 AI evidence database
```

---

### Phase 4 — Productionize Handoff to Inference Team

Goal: make evidence usable by the mathematical processing team.

Tasks:

```text
finalize export schema
freeze versioned evidence snapshots
document field definitions
add evidence quality reports
add source coverage reports
add collection reproducibility logs
```

Deliverable:

```text
versioned evidence corpus ready for intelligent processing
```

---

## 21. Success Criteria

The data collection team succeeds if:

```text
Every evidence item is traceable to a source.
Every document has source metadata.
Every collector reports success or failure status.
Evidence can be exported cleanly.
Raw documents can be reprocessed.
Company identifiers are reliable.
The mathematical team can process evidence without needing to know source-specific API details.
The system avoids mixing collection logic with scoring logic.
```

---

## 22. Non-Negotiable Design Rules

```text
Do not score companies in the collection layer.
Do not confuse keyword hits with AI maturity.
Do not discard raw source information.
Do not store evidence without source URLs or dates.
Do not mix company aliases without explicit mapping.
Do not allow silent collector failures.
Do not overwrite evidence without versioning.
Do not make the inference team depend on unstable source APIs.
```

---

## 23. Final Deliverable of the Data Collection Team

The final deliverable is not an AI score.

The final deliverable is a versioned, auditable, structured evidence corpus:

```text
Company Universe
+ Raw Documents
+ Extracted Candidate Evidence
+ Source Metadata
+ Collector Status
+ Export Interface
```

This corpus becomes the input to the mathematical inference team.
