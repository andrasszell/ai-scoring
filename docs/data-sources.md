# Data Sources

Operational companion to the platform registry and
**[§6A Data Platform Decisions](data-collection-initial-plan.md#6a-data-platform-decisions)**.

## Where platform metadata lives

| When | Source of truth | How to change |
|---|---|---|
| **Now (interim)** | This doc + §6A tables in the initial plan | Edit both + change-log |
| **Phase 1 (live file)** | [`config/platforms.yaml`](../config/platforms.yaml) | Edit YAML; sync this doc after loader wired (Step 1.8) |

See **[§6A.4 Platform registry](data-collection-initial-plan.md#6a4-platform-registry-single-source-of-truth)**
for the schema, consumers, and the five-step change workflow.

**Rule:** do not add platform details only to markdown or only to Python constants.
The registry (once live) is the approval record; collectors implement fetch logic.

---

## Phase 1 — approved platforms (interim table)

> Will be generated from `config/platforms.yaml` once the registry is implemented.

### Company universe

| Loader | Platform | Env | Collector CLI |
|---|---|---|---|
| S&P 500 list | Wikipedia (HTML table) | `SEC_USER_AGENT` (HTTP User-Agent) | `ai-collect load-companies` |
| CIK + SEC filer fallback | SEC `company_tickers.json` | `SEC_USER_AGENT` | (auto on `analyze` fallback) |

### Evidence collectors

| Collector | `source_type` | Platform / API | Env key | Required? |
|---|---|---|---|---|
| `sec_filings` | `sec_annual_filing` | SEC EDGAR | `SEC_USER_AGENT` | Yes (contact string) |
| `earnings_calls` | `earnings_call_transcript` | Financial Modeling Prep | `FMP_API_KEY` | Optional (skipped if missing) |
| `web_products` | `web_search_product` | SerpAPI → Google web | `SERPAPI_API_KEY` | Optional |
| `hiring_jobs` | `job_posting` | SerpAPI → Google Jobs | `SERPAPI_API_KEY` | Optional |
| `patents` | `patent` | PatentsView Search API | `PATENTSVIEW_API_KEY` | Optional |
| `research` | `research_paper` | Semantic Scholar Graph API | `SEMANTIC_SCHOLAR_API_KEY` | Optional (429-prone without) |

Run a subset: `ai-collect collect --source sec hiring --ticker MSFT`

Future: `ai-collect show-platforms` — list all registry entries with key status.

---

## Source categories (controlled vocabulary)

Applied automatically on every evidence row (`source_category`,
`source_reliability`, `confidence_initial`). Defaults from registry →
`src/evidence_collection/sources.py`.

`official_company`, `regulatory_filing`, `job_posting`, `press_release`,
`technical_blog`, `product_documentation`, `news_article`,
`third_party_database`, `social_media`, `unknown`.

## Reliability and initial confidence (Phase 1 defaults)

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
`official_company / high` (`sources.refine_for_url`). Backfilling
`companies.website_domain` is a Phase 1 task.

---

## Phase 3 premium vendors (evaluate — not approved)

Register in `platforms.yaml` with `phase: 3`, `enabled: false` when the registry
exists. See [§6A.1 evaluation criteria](data-collection-initial-plan.md#6a1-evidence-source-platforms-phase-1--approved).

Candidates: Lightcast, Revelio, Coresignal, Proxycurl, LinkedIn Talent Insights,
AlphaSense, FactSet, PitchBook, CB Insights, Similarweb, BuiltWith.

---

## Changing an approved platform

Follow **[§6A.4 change workflow](data-collection-initial-plan.md#6a4-platform-registry-single-source-of-truth)**:

1. Edit `config/platforms.yaml`
2. Update collector adapter (if needed)
3. Tests + `ai-collect validate`
4. Sync this doc + `change-log.md`
