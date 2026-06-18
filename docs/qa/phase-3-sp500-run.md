# Phase 3 full S&P 500 run — Block 3A.7

Manual QA record for the production-scale collect. Corpus at `data/evidence.sqlite`;
export at `data/exports/phase3_sp500_YYYYMMDD/` (local, gitignored).

## Prerequisites

- Phase 3A.1–3A.6 complete (pilot validated, retry/freshness tooling).
- Universe loaded: `ai-collect verify-universe` — ≥490 companies, all with CIK.
- API keys: `SEC_USER_AGENT`, `SERPAPI_API_KEY`, `FMP_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY`
  (optional: `GITHUB_TOKEN`; `PATENTSVIEW_API_KEY` until USPTO ODP migration).

## Commands

```bash
# One-shot (logs under data/exports/phase3_sp500_YYYYMMDD/)
bash scripts/phase3_sp500_run.sh

# If collect was started separately, finish validate/export:
PHASE=post DATE_TAG=20260618 bash scripts/phase3_sp500_run.sh

# Or step by step:
ai-collect load-companies
ai-collect verify-universe
ai-collect collect --all
ai-collect validate
ai-collect costs --project-full-sp500
ai-collect freshness --stale-only
ai-collect export-all --output-dir data/exports/phase3_sp500_YYYYMMDD
```

## Run status

| Field | Value |
|---|---|
| Date | 2026-06-18 |
| Run ID | _(in progress — see `collect.log`)_ |
| Companies | 509 loaded |
| Scope | `collect --all` (9 collectors) |
| Est. duration | ~6–10 h (rate limits on research / SerpAPI) |
| Est. API cost | ~$30–35 (linear from 50-ticker pilot ~$3.13) |
| Log | `data/exports/phase3_sp500_20260618/collect.log` |

**Monitor progress:**

```bash
tail -f data/exports/phase3_sp500_20260618/collect.log
sqlite3 data/evidence.sqlite "
  SELECT run_id, COUNT(DISTINCT ticker) tickers, COUNT(*) pairs
  FROM collector_status WHERE run_id=(SELECT MAX(id) FROM collector_runs)
  GROUP BY run_id;"
```

## Results

| Metric | Value |
|---|---|
| Evidence rows | _(fill after collect)_ |
| `ai-collect validate` violations | _(fill)_ |
| Est. API cost (run) | _(fill)_ |
| Runtime | _(fill)_ |

## Per-collector outcomes (latest status)

| Collector | success | no_results | api_key_missing | source_unavailable | rate_limited |
|---|---|---|---|---|---|
| sec_filings | | | | | |
| research | | | | | |
| web_products | | | | | |
| hiring_jobs | | | | | |
| press_releases | | | | | |
| product_docs | | | | | |
| earnings_calls | | | | | |
| patents | | | | | |
| github_repos | | | | | |

_Query after run:_

```bash
sqlite3 data/evidence.sqlite "
SELECT collector_name, status, COUNT(*) FROM collector_status
WHERE id IN (SELECT MAX(id) FROM collector_status GROUP BY ticker, source_type)
GROUP BY collector_name, status ORDER BY 1, 2;"
```

## Known gaps (expected)

- **Patents:** `api_key_missing` until PatentsView replacement (USPTO ODP).
- **GitHub:** `no_results` for tickers without `company_github_orgs.yaml` entries.
- **Earnings:** many `no_results` on current FMP plan (source-empty, not failure).
- **SerpAPI / product_docs:** transient `source_unavailable` — run `ai-collect retry-failed` after main collect.

## Post-run checklist

- [ ] `ai-collect validate` — 0 violations
- [ ] Export archived under `data/exports/phase3_sp500_YYYYMMDD/`
- [ ] Cost report saved (`costs.log` or `ai-collect costs`)
- [ ] `ai-collect retry-failed` for transient failures (optional)
- [ ] Spot-check 5–10 tickers per [`phase-1-spot-check.md`](phase-1-spot-check.md) rubric

## API keys at run time

- Set: _(fill)_
- Missing: _(fill)_
