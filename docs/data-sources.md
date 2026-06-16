# Data Sources

Approved data sources and the source-quality rules they map to (Coding Standards §6).
The classification lives in code at `src/evidence_collection/sources.py` and is
applied automatically to every evidence item (`source_category`,
`source_reliability`, `confidence_initial`).

## Source categories (controlled vocabulary)

`official_company`, `regulatory_filing`, `job_posting`, `press_release`,
`technical_blog`, `product_documentation`, `news_article`,
`third_party_database`, `social_media`, `unknown`.

## Reliability levels

`high`, `medium`, `low`, `unknown`.

## Active sources (Phase 1)

| Collector | `source_type` | Category | Reliability | Initial confidence | Key |
|---|---|---|---|---:|---|
| `sec_filings` | `sec_annual_filing` | regulatory_filing | high | 0.75 | none (`SEC_USER_AGENT`) |
| `earnings_calls` | `earnings_call_transcript` | official_company | high | 0.70 | `FMP_API_KEY` |
| `web_products` | `web_search_product` | news_article | low | 0.40 | `SERPAPI_API_KEY` |
| `hiring_jobs` | `job_posting` | job_posting | medium | 0.50 | `SERPAPI_API_KEY` |
| `patents` | `patent` | regulatory_filing | medium | 0.55 | `PATENTSVIEW_API_KEY` |
| `research` | `research_paper` | third_party_database | medium | 0.45 | optional |

## Source-quality rules (Coding Standards §6)

- Official company sources are **claims with context**, not automatically true.
- News/web-search results are **secondary** unless they contain direct company
  statements — hence `web_search_product` defaults to `low`.
- Job postings are strong evidence of **capability demand**, not deployed AI.
- Vendor case studies are useful but must be marked potentially promotional.
- One weak source must not dominate a company score (enforced in the inference layer
  via caps).

## Initial confidence vs interpretation

`confidence_initial` is a **source prior** assigned at collection time from the
reliability of the source — it is provenance metadata, not an interpretation of
what the evidence means. The inference layer may override it with a computed
confidence.

## Per-domain refinement (implemented)

A row whose URL is on the company's own `website_domain` is upgraded to
`official_company / high` (`sources.refine_for_url`). This currently triggers only
when `companies.website_domain` is populated — backfilling that field is a Phase 1
task.

## Planned refinements

- Backfill `companies.website_domain` so the per-domain refinement activates.
- Add `press_release`, `technical_blog`, `product_documentation`, `github`
  (Phase 2 sources) to the table above as they are implemented.
