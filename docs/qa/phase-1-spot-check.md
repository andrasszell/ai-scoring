# Phase 1 QA spot-check (Block D Step 4.4)

Manual review of five companies from the validation corpus after Run #11  
(`ai-collect collect --validation-set`, 2026-06-16).

**Corpus summary:** 991 evidence rows across 35 companies; `ai-collect validate` → 0 violations.

---

## 1. MSFT — Microsoft (mega-cap / Technology)

| Collector | Evidence rows | Last status |
|-----------|---------------|-------------|
| sec_filings | 15 | success |
| web_products | 8 | success |
| research | 10 | source_unavailable (latest run; rows from prior success) |
| hiring_jobs | 0 | no_results |
| patents | 0 | api_key_missing |
| earnings_calls | 0 | api_key_missing |

**Sample rows reviewed**

1. **sec_filings** — 10-K paragraph on AI / Copilot. URL opens on sec.gov; filing date `2025-07-30`; text is plausible regulatory disclosure.
2. **web_products** — `microsoft.com/en-us/ai` product page. Source date retrieval fallback; high-reliability `official_company` category correct for own domain.
3. **research** — Semantic Scholar paper mentioning Microsoft + ML. URL opens; year anchor `2025-01-01`; abstract text matches title (third-party academic mention, not a product claim).

**False positives?** SEC keyword hits on generic “automation” are possible but sampled paragraphs are genuinely AI-related.

**Anomalies:** Google Jobs empty for MSFT (`no_results`); hiring works for other tickers (see JPM/NVDA).

---

## 2. JPM — JPMorgan Chase (mega-cap / Financials)

| Collector | Evidence rows | Last status |
|-----------|---------------|-------------|
| sec_filings | 8 | success |
| web_products | 10 | success |
| hiring_jobs | 10 | success |
| research | 10 | success |
| patents | 0 | api_key_missing |
| earnings_calls | 0 | api_key_missing |

**Sample rows reviewed**

1. **hiring_jobs** — “Applied AI ML Researcher Lead” via LinkedIn. `source_date`: `7 days ago`; apply URL opens; title/location plausible.
2. **web_products** — Third-party article on JPM AI initiatives. Low-reliability `news_article`; URL and snippet consistent.
3. **sec_filings** — 10-K AI risk/disclosure paragraph. Filing date present; EDGAR URL valid.

**False positives?** Hiring rows match AI/ML role filter; no obvious off-topic jobs in sample.

**Anomalies:** None material.

---

## 3. NVDA — Nvidia (mega-cap / Technology)

| Collector | Evidence rows | Last status |
|-----------|---------------|-------------|
| sec_filings | 16 | success |
| web_products | 8 | success |
| hiring_jobs | 10 | success |
| research | 10 | success |
| patents | 0 | api_key_missing |
| earnings_calls | 0 | api_key_missing |

**Sample rows reviewed**

1. **hiring_jobs** — “Senior Machine Learning Engineer - Physical AI” on jobs.nvidia.com. Retrieval date fallback when posting time absent; first-party URL.
2. **hiring_jobs** — “Applied ML Engineer – New College Grad 2026” with `3 days ago` origin date.
3. **sec_filings** — 10-K section on AI/datacenter demand. Date and URL valid; high-signal regulatory evidence.

**False positives?** None in sample; NVIDIA-specific AI content expected.

**Anomalies:** None.

---

## 4. PLTR — Palantir (mid-cap AI / Technology)

| Collector | Evidence rows | Last status |
|-----------|---------------|-------------|
| sec_filings | 10 | success |
| web_products | 9 | success |
| hiring_jobs | 0 | no_results |
| research | 0 | source_unavailable |
| patents | 0 | api_key_missing |
| earnings_calls | 0 | api_key_missing |

**Sample rows reviewed**

1. **sec_filings** — 10-K AI platform disclosure. Filing date `2026-02-17`; sec.gov URL opens.
2. **web_products** — Palantir AIP / platform search result. Mix of official and news URLs; snippets mention AI platform.
3. **web_products** — Third-party comparison article. Correctly classified as low-reliability news.

**False positives?** Web results may include generic “AI platform” listicles; acceptable for Phase 1 high-recall collection.

**Anomalies:** Google Jobs empty for PLTR; SEC + web still provide coverage.

---

## 5. ELAN — Elanco Animal Health (SEC fallback / Health Care)

| Collector | Evidence rows | Last status |
|-----------|---------------|-------------|
| sec_filings | 2 | success |
| web_products | 7 | success |
| hiring_jobs | 3 | success |
| research | 0 | source_unavailable |
| patents | 0 | api_key_missing |
| earnings_calls | 0 | api_key_missing |

**Entity resolution:** Not in S&P 500 table; loaded via SEC `company_tickers.json` fallback. CIK `0001739104`, domain `elanco.com` from config.

**Sample rows reviewed**

1. **sec_filings** — 10-K with limited AI keyword hits (2 paragraphs). Validates SEC path for non-index names.
2. **hiring_jobs** — “Senior Director-Data Science” / “Applied ML Engineer”. URLs open; dates mix origin (`25 days ago`) and retrieval fallback.
3. **web_products** — Elanco digital/ag-tech search results. Snippets plausible; some third-party job-aggregator noise.

**False positives?** Animal-health context may produce weaker AI signal than tech names; corpus size appropriately small.

**Anomalies:** SEC fallback path works; sector null until enriched from external source (acceptable).

---

## Cross-cutting observations

| Topic | Finding |
|-------|---------|
| Source dates | All rows have URL and/or date; no validation violations |
| Optional keys | FMP + PatentsView skipped cleanly (`api_key_missing`) |
| Semantic Scholar | ~27/35 `source_unavailable` in Run #11 (rate limit); 8 successes + retained prior rows |
| Google Jobs | 7/35 `no_results`; 28/35 success when listings exist |
| Export bundle | `data/exports/phase1_20260616/` (local; not committed) |

**Reviewer sign-off:** Spot-check supports proceeding to Phase 2 platform expansion.
