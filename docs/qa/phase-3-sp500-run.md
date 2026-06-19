# Phase 3 full S&P 500 run — Block 3A.7

Manual QA record for the production-scale collect. Corpus at `data/evidence.sqlite`;
export at `data/exports/phase3_sp500_20260619/` (local, gitignored).

## Commands

```bash
ai-collect collect --all --source sec research earnings github
PHASE=post DATE_TAG=20260619 bash scripts/phase3_sp500_run.sh
```

## Run status

| Field | Value |
|---|---|
| Date | 2026-06-19 |
| Run ID | **#26** (completed) |
| Companies | 509 |
| Scope | `collect --all --source sec research earnings github` |
| Runtime | ~49 min (12:26–13:15 UTC) |
| SerpAPI | Not in run #26 — pilot-era rows only (~50 tickers); quota exhausted 2026-06-18 |

## Results

| Metric | Value |
|---|---|
| Evidence rows | **9,291** across **509** companies |
| `ai-collect validate` violations | **0** |
| Est. API cost (run #26) | **~$25.45** (FMP transcript probes; SEC/research free) |
| Export | `data/exports/phase3_sp500_20260619/` |

## Per-collector outcomes (latest status per ticker×source)

| Collector | success | no_results | api_key_missing | source_unavailable | rate_limited |
|---|---|---|---|---|---|
| sec_filings | 484 | 25 | — | — | — |
| research | 507 | — | — | 1 | 1 |
| earnings_calls | — | 509 | — | — | — |
| github_repos | 1 | 505 | — | 3 | — |
| web_products | 32 | — | — | 21 | — |
| hiring_jobs | 25 | 7 | — | 21 | — |
| press_releases | 31 | — | — | 22 | — |
| product_docs | 26 | 4 | — | 23 | — |
| patents | — | — | 53 | — | — |

SerpAPI/patent columns reflect **pilot-era** collection (50 tickers) plus gaps; run #26
did not refresh those pillars.

## Known gaps (accepted)

- **SerpAPI:** quota exhausted — refresh products/hiring/press/product_docs after top-up.
- **Patents:** `api_key_missing` (PatentsView API unavailable).
- **Earnings:** 509× `no_results` on current FMP plan (source-empty).
- **GitHub:** sparse without expanded `company_github_orgs.yaml`.

## Post-run checklist

- [x] `ai-collect validate` — 0 violations
- [x] Export archived under `data/exports/phase3_sp500_20260619/`
- [x] Cost report saved (`costs.log`)
- [ ] `ai-collect retry-failed` for SerpAPI/research pairs (after SerpAPI top-up)
- [ ] Spot-check 5–10 tickers per [`phase-1-spot-check.md`](phase-1-spot-check.md) rubric

## API keys at run time

- Set: `SEC_USER_AGENT`, `SERPAPI_API_KEY` (quota exhausted), `FMP_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY`
- Missing: `PATENTSVIEW_API_KEY`, `GITHUB_TOKEN`
