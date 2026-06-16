# Implementation Plan for Data Collection Team

## AI Adoption Intelligence Platform — Evidence Discovery Layer

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

The existing SQLite approach is appropriate for MVP.

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

The current project already uses:

```text
companies
documents
ai_evidence
metrics
```

The `metrics` table should eventually move out of the collection layer or be restricted to collection metrics only.

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

Also support:

```text
JSONL evidence export
SQLite database snapshot
Parquet export
API endpoint
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
improve error handling
add collector status
add source dates
store raw documents or raw API responses
deduplicate exact records
add tests
validate sample companies
```

Deliverable:

```text
high-quality evidence corpus for 25–50 companies
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
