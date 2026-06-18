# Phase 3 pilot run — 50 tickers (2026-06-16)

Manual QA record for Block 3A.2. Corpus at `data/evidence.sqlite`; export at
`data/exports/phase3_pilot_20260616/` (local, gitignored).

## Commands

```bash
ai-collect load-companies --pilot-set
ai-collect collect --pilot-set
ai-collect collect --pilot-set --source earnings   # FMP after key added
ai-collect collect --source research --ticker ...  # Semantic Scholar retry
ai-collect retry-failed
ai-collect validate
ai-collect costs --project-full-sp500
ai-collect export-all --output-dir data/exports/phase3_pilot_20260616
```

## Results (post-retry baseline)

| Metric | Value |
|---|---|
| Pilot tickers | 50 (`config/phase3_pilot_companies.yaml`) |
| Evidence rows | ~2,150+ |
| `ai-collect validate` | 0 violations |
| Est. API cost (pilot run #13) | ~$3.13 |
| Full S&P projection | ~$32/run (linear from 50-ticker basis) |

## Latest status per collector (50 tickers)

| Collector | Typical outcome | Notes |
|---|---|---|
| sec_filings | success | 50/50 |
| research | success | 50/50 after API key + manual retry |
| web_products / hiring / press / product_docs | mixed | SerpAPI; use `retry-failed` for transient HTTP failures |
| earnings_calls | no_results | FMP key ok; no transcripts for many tickers on current plan |
| patents | api_key_missing | PatentsView Search API unavailable — migrate to USPTO ODP |
| github_repos | no_results | Only tickers with `company_github_orgs.yaml` entries |

## Known gaps (accepted for pilot)

- Patents pillar not measured until new data source.
- GitHub pillar sparse without expanded org metadata.
- Earnings `no_results` is source-empty, not collection failure.
- Some SerpAPI/product_docs pairs remain `source_unavailable` after `retry-failed`
  run #21 (70/70 still failed — transient HTTP); pillar excluded from score per Block F.

## Next

- **3A.5** — `--stale-days` incremental refresh
- **3A.7** — full `collect --all` after ops tooling complete
