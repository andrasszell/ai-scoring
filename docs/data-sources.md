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
The SEC filer list is also used as the fallback universe for `ai-collect analyze`.

### Evidence collectors (Phase 1 — enabled)

| ID | Collector | CLI | `source_type` | Platform | Env | Category | Reliability | Conf. | Cost |
|---|---|---|---|---|---|---|---|---|---|
| `sec_edgar` | `sec_filings` | `sec` | `sec_annual_filing` | SEC EDGAR | `SEC_USER_AGENT` (required) | regulatory_filing | high | 0.75 | free |
| `fmp_transcripts` | `earnings_calls` | `earnings` | `earnings_call_transcript` | Financial Modeling Prep | `FMP_API_KEY` (optional) | official_company | high | 0.70 | paid |
| `serpapi_web` | `web_products` | `products` | `web_search_product` | SerpAPI Google web | `SERPAPI_API_KEY` (optional) | news_article | low | 0.40 | paid |
| `serpapi_jobs` | `hiring_jobs` | `hiring` | `job_posting` | SerpAPI Google Jobs | `SERPAPI_API_KEY` (optional) | job_posting | medium | 0.50 | paid |
| `patentsview` | `patents` | `patents` | `patent` | PatentsView Search API | `PATENTSVIEW_API_KEY` (optional) | regulatory_filing | medium | 0.55 | free |
| `semantic_scholar` | `research` | `research` | `research_paper` | Semantic Scholar Graph API | `SEMANTIC_SCHOLAR_API_KEY` (optional) | third_party_database | medium | 0.45 | free |

Run a subset: `ai-collect collect --source sec hiring --ticker MSFT`

Inspect registry + key status: `ai-collect show-platforms` (phase 1 enabled) or
`ai-collect show-platforms --all` (all phases, including disabled stubs).

Collectors declare matching `platform_id` in code (see `collectors/base.py`).

---

## Phase 2 — planned (registry stubs, disabled)

| ID | Collector | `source_type` | Display name | Enabled |
|---|---|---|---|---|
| `github_repos` | `github_repos` | `github_repository` | GitHub public repositories | no |
| `press_releases` | `press_releases` | `press_release` | Company press releases | no |
| `product_documentation` | `product_docs` | `product_documentation` | Product and developer documentation | no |

Collectors not implemented — YAML-only until adapters exist.

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

Every collector run must be explainable when evidence count is zero. See
[`data-collection-initial-plan.md` §12](data-collection-initial-plan.md#12-collection-status-and-failure-handling)
and the implementation plan
[`post-phase-1-collection-outcomes-plan.md`](post-phase-1-collection-outcomes-plan.md).

### Controlled reason codes (`collector_status.message`)

When `status` is `success` or `no_results`, collectors should set:

```text
reason:source_empty       # API OK; origin returned nothing for this company/query
reason:filtered_to_zero   # Origin had material; zero evidence rows after filter/extract
reason:partial_success    # Some evidence; run hit caps/limits (optional)
```

### How to read a status row

| `status` | Typical `message` | `documents_count` | Interpretation |
|---|---|---|---|
| `success` | — or `reason:partial_success` | any | Evidence and/or documents collected |
| `no_results` | `reason:source_empty` | 0 | Source had nothing to offer |
| `no_results` | `reason:filtered_to_zero` | ≥1 **or** `source_hits` ≥1 | **Not** “company has no AI” |
| `source_unavailable` / `rate_limited` | error detail | — | **Unknown** — re-run later |
| `api_key_missing` / `skipped` | key/platform detail | — | **Not measured** |

All Phase 1 collectors emit `reason:…` on `no_results` rows (Block F complete).
`ai-collect validate` gates on `missing_outcome_reason` for latest status per source.

Inspect: `ai-collect status`, `ai-collect validate-company TICKER`.

---

## Changing an approved platform

Follow **[§6A.4 change workflow](data-collection-initial-plan.md#6a4-platform-registry-single-source-of-truth)**:

1. Edit `config/platforms.yaml`
2. Update collector adapter (if needed)
3. Tests + `ai-collect validate`
4. Sync this doc (`python scripts/sync_platform_docs.py --all`) + `change-log.md`
