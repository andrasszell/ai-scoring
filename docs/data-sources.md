# Data Sources

Operational companion to the platform registry and
**[§6A Data Platform Decisions](data-collection-initial-plan.md#6a-data-platform-decisions)**.

> **Synced from [`config/platforms.yaml`](../config/platforms.yaml) on 2026-06-16**
> (registry v1.0). Do not edit platform tables here independently — update the YAML,
> then re-sync this doc and add a change-log entry. Regenerate tables with:
> `python scripts/sync_platform_docs.py --all`

## Where platform metadata lives

| Source of truth | Location | How to change |
|---|---|---|
| **Platform registry (live)** | [`config/platforms.yaml`](../config/platforms.yaml) | Edit YAML → collector/tests → sync this doc → change-log |
| Runtime loader | `src/evidence_collection/platforms.py` | Schema validation at load time |
| Reliability defaults | Registry first → `sources.py` fallback | Set per-platform fields in YAML |
| CLI inspection | `ai-collect show-platforms [--all] [--phase N]` | Read-only; no DB required |

See **[§6A.4 Platform registry](data-collection-initial-plan.md#6a4-platform-registry-single-source-of-truth)**
for schema, consumers, and the five-step change workflow.

**Rule:** do not add platform details only to markdown or only to Python constants.
The registry is the approval record; collectors implement fetch logic.

---

## Phase 1 — approved platforms

### Company universe loaders

| ID | Display name | Vendor | Env | Phase | Enabled | CLI |
|---|---|---|---|---|---|---|
| `wikipedia_sp500` | Wikipedia S&P 500 constituents | Wikimedia Foundation | `SEC_USER_AGENT` (required) | 1 | yes | `load-companies` |
| `sec_company_tickers` | SEC company tickers | U.S. Securities and Exchange Commission | `SEC_USER_AGENT` (required) | 1 | yes | `load-companies` |

CLI: `ai-collect load-companies` merges Wikipedia sector/industry with SEC CIKs.
The SEC filer list is also used as the fallback universe for on-demand company
resolution (`analyze`, `score --company`, `run --company`). See
[`phase-2-implementation.md` § Block 2.0](phase-2-implementation.md#block-20--on-demand-company-scoring).

### Evidence collectors (Phase 1 — enabled)

| ID | Collector | CLI | `source_type` | Platform | Env | Category | Reliability | Conf. | Cost |
|---|---|---|---|---|---|---|---|---|---|
| `sec_edgar` | `sec_filings` | `sec` | `sec_annual_filing` | SEC EDGAR | `SEC_USER_AGENT` (required) | regulatory_filing | high | 0.75 | free |
| `fmp_transcripts` | `earnings_calls` | `earnings` | `earnings_call_transcript` | Financial Modeling Prep | `FMP_API_KEY` (optional) | official_company | high | 0.70 | paid |
| `serpapi_web` | `web_products` | `products` | `web_search_product` | SerpAPI Google web | `SERPAPI_API_KEY` (optional) | news_article | low | 0.40 | paid |
| `serpapi_jobs` | `hiring_jobs` | `hiring` | `job_posting` | SerpAPI Google Jobs | `SERPAPI_API_KEY` (optional) | job_posting | medium | 0.50 | paid |
| `patentsview` | `patents` | `patents` | `patent` | PatentsView Search API | `PATENTSVIEW_API_KEY` (optional) | regulatory_filing | medium | 0.55 | free |
| `semantic_scholar` | `research` | `research` | `research_paper` | Semantic Scholar Graph API | `SEMANTIC_SCHOLAR_API_KEY` (optional) | third_party_database | medium | 0.45 | free |

Run a subset: `ai-collect collect --source sec github press product_docs --ticker MSFT`

Inspect registry + key status: `ai-collect show-platforms` (enabled collectors) or
`ai-collect show-platforms --all` (all phases, including disabled stubs).

Collectors declare matching `platform_id` in code (see `collectors/base.py`).

---

## Phase 2 — GitHub (enabled)

| ID | Collector | CLI | `source_type` | Display name | Env | Enabled |
|---|---|---|---|---|---|---|
| `github_repos` | `github_repos` | `github` | `github_repository` | GitHub public repositories | `GITHUB_TOKEN` (optional) | yes |

Org slugs per ticker: [`config/company_github_orgs.yaml`](../config/company_github_orgs.yaml).
Without a configured org list the collector reports `reason:source_empty` (no guessing).

```bash
ai-collect collect --source github --ticker MSFT NVDA
```

## Phase 2 — Press releases (enabled)

| ID | Collector | CLI | `source_type` | Display name | Env | Enabled |
|---|---|---|---|---|---|---|
| `press_releases` | `press_releases` | `press` | `press_release` | Company press releases | `SERPAPI_API_KEY` (optional) | yes |

Uses the same SerpAPI key as products/hiring. When `website_domain` is set the
query is `site:{domain}` for first-party press pages.

```bash
ai-collect collect --source press --ticker MSFT
```

## Phase 2 — Product documentation (enabled)

| ID | Collector | CLI | `source_type` | Display name | Env | Enabled |
|---|---|---|---|---|---|---|
| `product_documentation` | `product_docs` | `product_docs` | `product_documentation` | Product and developer documentation | `SERPAPI_API_KEY` (optional) | yes |

Discovers first-party documentation via SerpAPI (`site:{website_domain}`), fetches
pages, stores text for offline reprocess. Requires `website_domain` on the company.

```bash
ai-collect collect --source product_docs --ticker MSFT
ai-collect reprocess --source product_docs --ticker MSFT
```

## Phase 2 — planned

All Phase 2 registry collectors are now implemented. Remaining work is validation
at scale and optional vendor swaps — see [`phase-3-development-plan.md`](phase-3-development-plan.md).

---

## Phase 3 — premium vendors (evaluate — not approved)

Registered in `platforms.yaml` with `phase: 3`, `enabled: false`:

| ID | Collector | Vendor | Env | Notes |
|---|---|---|---|---|
| `lightcast` | `lightcast_hiring` | Lightcast | `LIGHTCAST_API_KEY` (required) | Workforce/hiring alternative to SerpAPI jobs |
| `alphasense` | `alphasense_transcripts` | AlphaSense | `ALPHASENSE_API_KEY` (required) | Premium transcript/search alternative to FMP |
| `revelio` | `revelio_workforce` | Revelio Labs | `REVELIO_API_KEY` (required) | Workforce/hiring analytics |

See [§6A.1 evaluation criteria](data-collection-initial-plan.md#6a1-evidence-source-platforms-phase-1--approved).

Other candidates from the strategic plan (not yet in registry): Coresignal, Proxycurl,
LinkedIn Talent Insights, FactSet, PitchBook, CB Insights, Similarweb, BuiltWith.

---

## Source categories (controlled vocabulary)

Applied automatically on every evidence row (`source_category`,
`source_reliability`, `confidence_initial`). Values loaded from registry via
`src/evidence_collection/sources.py` (`profile_for`).

`official_company`, `regulatory_filing`, `job_posting`, `press_release`,
`technical_blog`, `product_documentation`, `news_article`,
`third_party_database`, `social_media`, `unknown`.

## Reliability and initial confidence (from registry)

| `source_type` | Category | Reliability | `confidence_initial` |
|---|---|---|---|
| `sec_annual_filing` | regulatory_filing | high | 0.75 |
| `earnings_call_transcript` | official_company | high | 0.70 |
| `web_search_product` | news_article | low | 0.40 |
| `job_posting` | job_posting | medium | 0.50 |
| `patent` | regulatory_filing | medium | 0.55 |
| `research_paper` | third_party_database | medium | 0.45 |
| `github_repository` | third_party_database | medium | 0.50 |
| `press_release` | press_release | medium | 0.45 |
| `product_documentation` | product_documentation | high | 0.65 |

## Source-quality rules (Coding Standards §6)

- Official company sources are **claims with context**, not automatically true.
- News/web-search results are **secondary** unless they contain direct company
  statements — hence `web_search_product` defaults to `low`.
- Job postings are strong evidence of **capability demand**, not deployed AI.
- Vendor case studies are useful but must be marked potentially promotional.
- One weak source must not dominate a company score (enforced in the inference layer).

## Per-domain refinement (implemented)

A row whose URL is on the company's own `website_domain` is upgraded to
`official_company / high` (`sources.refine_for_url`). Domains are seeded from
[`config/company_domains.yaml`](../config/company_domains.yaml) on `load-companies`.
Search aliases live in [`config/company_aliases.yaml`](../config/company_aliases.yaml).
GitHub org slugs: [`config/company_github_orgs.yaml`](../config/company_github_orgs.yaml).
Inspect one company: `ai-collect validate-company MSFT`.

## Phase 1 validation sample (Block D)

| Source | Location | CLI |
|---|---|---|
| Validation company list | [`config/validation_companies.yaml`](../config/validation_companies.yaml) | `collect --validation-set` |
| Loader | `src/evidence_collection/universe/validation.py` | `load-companies --validation-set` |

35 tickers (mega-cap default universe, sector spread, mid-cap AI names, SEC-fallback
filers such as ELAN). Tickers not in the S&P 500 load are upserted from the SEC
`company_tickers.json` map. Website domains for the set live in
[`config/company_domains.yaml`](../config/company_domains.yaml).

```bash
ai-collect load-companies --validation-set   # S&P 500 + ensure validation tickers
ai-collect collect --validation-set          # collect all 35 (do not combine with --ticker)
ai-collect export-all --output-dir data/exports/phase1_YYYYMMDD
```

QA notes: [`docs/qa/`](qa/).

## Collection outcome semantics

Every collector run must be explainable when evidence count is zero (Block F,
complete). Strategic context: [`data-collection-initial-plan.md` §12](data-collection-initial-plan.md#12-collection-status-and-failure-handling).

### Status vocabulary (`collector_status.status`)

| `status` | Meaning |
|---|---|
| `success` | Run completed; see counters and `reason:` prefix in `message` |
| `no_results` | Run completed with **zero evidence rows inserted** |
| `api_key_missing` | Not attempted — required/optional key absent |
| `api_limit_reached` | Not completed — quota exhausted |
| `source_unavailable` | Attempted — transport/API/parse failure |
| `rate_limited` | Attempted — throttled (e.g. HTTP 429) |
| `parse_failed` | Response received but unusable |
| `company_not_found` | Entity resolution failed (e.g. missing CIK) |
| `ambiguous_company` | Multiple entity matches |
| `skipped` | Registry gate (`enabled: false`) |

### Outcome reason codes (`collector_status.message`)

When `status` is `success` or `no_results`, collectors set a **`reason:` prefix**:

```text
reason:source_empty       # API OK; origin returned nothing for this company/query
reason:filtered_to_zero   # Origin had material; zero evidence rows after filter/extract
reason:partial_success    # Some evidence; run hit caps/limits (optional)
```

Stability rule: reason codes are a controlled vocabulary (`src/evidence_collection/outcomes.py`).
Add new codes only via `data-sources.md` + `change-log.md`.

### Counters on each run

| Field | Meaning |
|---|---|
| `evidence_count` | Evidence rows inserted this run |
| `documents_count` | Documents stored (SEC filing, earnings transcript, product doc, …) |
| `api_calls` | HTTP calls made |
| `source_hits` | Raw items returned by API before filtering |
| `candidates_after_filter` | Items surviving collector-specific filter |

### How to read a status row

| `status` | `outcome_reason` | `documents_count` | `source_hits` | Safe inference |
|---|---|---|---|---|
| `success` | — | ≥0 | ≥0 | Evidence exists |
| `no_results` | `source_empty` | 0 | 0 | Source empty for query |
| `no_results` | `filtered_to_zero` | ≥1 **or** hits ≥1 | ≥1 | **Not** proof of no AI activity |
| `source_unavailable` / `rate_limited` | — | — | — | **Unknown** — exclude pillar from score |
| `api_key_missing` / `skipped` | — | — | — | **Not measured** — exclude pillar |

All collectors (Phase 1 + Phase 2) emit `reason:…` on `no_results` rows.
`ai-collect validate` gates on `missing_outcome_reason` for latest status per source.

Inspect: `ai-collect status`, `ai-collect validate-company TICKER`.

---

## Changing an approved platform

Follow **[§6A.4 change workflow](data-collection-initial-plan.md#6a4-platform-registry-single-source-of-truth)**:

1. Edit `config/platforms.yaml`
2. Update collector adapter (if needed)
3. Tests + `ai-collect validate`
4. Sync this doc (`python scripts/sync_platform_docs.py --all`) + `change-log.md`
