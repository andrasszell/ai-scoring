# Data sources — investor brief

**AI Adoption Intelligence Platform · Evidence Discovery Layer**  
**Date:** June 2026 · **Universe:** S&P 500 (~509 companies)

This document summarizes the **public and licensed data sources** used to build our
auditable evidence corpus. It is intended for investors evaluating **ongoing API and
data subscription costs** for production-scale collection and refresh.

Technical detail: [`data-sources.md`](data-sources.md) · Platform registry:
[`config/platforms.yaml`](../config/platforms.yaml)

---

## What we collect

We gather **candidate evidence** of corporate AI adoption from nine independent signal
types (pillars). Each item is traceable to a source URL, collector version, and
collection timestamp. We do **not** score companies in this layer — scoring is a
separate inference step.

| Pillar | Source (vendor) | What it measures |
|---|---|---|
| SEC filings | U.S. SEC EDGAR | AI-related disclosures in annual reports (10-K, 20-F, 40-F) |
| Earnings calls | Financial Modeling Prep (FMP) | Management commentary on AI in earnings transcripts |
| Product / service mentions | SerpAPI (Google web) | Public web mentions of AI products and services |
| Hiring | SerpAPI (Google Jobs) | Job postings referencing AI / ML roles |
| Research papers | Semantic Scholar | Academic papers associated with the company |
| Patents | PatentsView (USPTO-derived) | U.S. patent filings with AI-related claims |
| GitHub | GitHub | Public open-source repositories under known company orgs |
| Press releases | SerpAPI (Google web) | Company press and announcement pages |
| Product documentation | SerpAPI + first-party fetch | Official product / developer documentation on company domains |

**Company universe** (ticker, CIK, sector) is loaded from **Wikipedia** (S&P 500 list)
and **SEC company tickers** — both free, with SEC fair-access requirements.

---

## Subscriptions, permissions, and current status

| Platform | Cost model | Subscription / access | Permissions & compliance | Production status (Jun 2026) |
|---|---|---|---|---|
| **SEC EDGAR** | Free | No account; **SEC_USER_AGENT** contact string required (fair-access policy) | U.S. government public filings; rate-limited client (~4 req/s) | **Active** — primary pillar; 50/50 pilot success |
| **Wikipedia + SEC tickers** | Free | Same User-Agent requirement | Public metadata for universe load | **Active** |
| **Financial Modeling Prep** | Paid API key | **FMP_API_KEY** — tier depends on plan | Vendor ToS; transcript access typically needs paid tier | **Key set** — collector runs; most tickers return *no transcript* on current plan (source-empty, not outage) |
| **SerpAPI** | Paid per search | **SERPAPI_API_KEY** — monthly search quota | Vendor ToS; aggregates Google web/jobs results; we store raw API responses | **Quota exhausted** (HTTP 429) — blocks products, hiring, press, product_docs until quota restored or plan upgraded |
| **Semantic Scholar** | Free (key recommended) | **SEMANTIC_SCHOLAR_API_KEY** — optional but avoids heavy rate limits | Academic Graph API ToS | **Active** with key — 50/50 pilot success |
| **PatentsView** | Free API key | **PATENTSVIEW_API_KEY** | USPTO-derived patent data | **Unavailable** — Search API shut down; migration to USPTO Open Data Portal planned |
| **GitHub** | Free | **GITHUB_TOKEN** optional (higher rate limits) | Public repo search only; org list in our config | **Active** — sparse coverage without expanded org metadata (~23 tickers configured) |

**Collectors without a key** record `api_key_missing` and skip gracefully — the run
continues for other sources.

---

## Estimated cost per full S&P 500 refresh

Based on Phase 3 **50-ticker pilot** (run #13, nine collectors, June 2026):

| Metric | Estimate |
|---|---|
| Pilot API cost (50 companies) | **~$3.13** |
| Linear projection (509 companies) | **~$30–35 per full refresh** |
| Dominant paid vendor | **SerpAPI** (~4 search-based collectors sharing one quota) |
| Second paid line item | **FMP** (earnings transcripts — cost scales if upgraded tier returns more transcripts) |

Estimates use internal planning rates in [`config/api_cost_estimates.yaml`](../config/api_cost_estimates.yaml)
(~$0.01/SerpAPI search). Actual billing follows vendor invoices.

**Refresh cadence (planned):** incremental re-collection with per-source TTLs (e.g.
SEC quarterly, jobs bi-weekly) — see [`config/source_freshness_ttl.yaml`](../config/source_freshness_ttl.yaml).

---

## What funding would unlock

| Investment area | Benefit |
|---|---|
| **SerpAPI plan upgrade / higher monthly quota** | Restore four web/job/press/docs pillars at S&P 500 scale; largest immediate gap |
| **FMP transcript tier** | Earnings-call pillar beyond SEC filings; management AI narrative |
| **GitHub org metadata expansion** | Broader open-source signal without new vendor |
| **USPTO / patent data migration** | Restore patent pillar after PatentsView deprecation |
| **Premium vendors (evaluation only)** | Lightcast or Revelio (hiring), AlphaSense (transcripts) — registered but not enabled |

Premium alternatives are listed in the platform registry (`phase: 3`, `enabled: false`)
and will be evaluated against SerpAPI/FMP on evidence quality, licensing, and cost at
scale before approval.

---

## Legal and operational notes

- All collection is **read-only** against vendor APIs and public URLs; raw documents
  and API responses are stored locally for audit and reprocessing.
- We respect vendor rate limits and fair-access policies (especially SEC EDGAR).
- Evidence is **candidate** material — scoring applies versioned rules and can exclude
  low-reliability or empty sources (e.g. SerpAPI failures, missing patents).
- No investor-facing deployment should rely on SerpAPI job/LinkedIn data as proof of
  deployed AI; hiring is a **demand signal** only.

---

## Summary for investors

| Item | Detail |
|---|---|
| **Core free stack** | SEC filings + Semantic Scholar + GitHub (partial) — production-viable today |
| **Paid stack in use** | SerpAPI (four pillars) + FMP (earnings) |
| **Near-term blocker** | SerpAPI search quota — ~$30–35/run at S&P scale once quota available |
| **Known gaps** | Patents (API sunset), earnings (plan limits), GitHub (metadata coverage) |
| **Upgrade path** | Higher SerpAPI/FMP tiers now; premium vendors evaluated in Phase 3B |

For questions on methodology or scoring weights, see [`scoring-methodology.md`](scoring-methodology.md).
