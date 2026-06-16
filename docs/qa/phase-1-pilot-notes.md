# Phase 1 pilot collection notes (Block D Step 4.2)

**Date:** 2026-06-16  
**Command:** `ai-collect collect --ticker MSFT GOOGL JPM` (all enabled sources)

## API keys available

| Key | Status |
|-----|--------|
| `SEC_USER_AGENT` | Set |
| `SERPAPI_API_KEY` | Set |
| `FMP_API_KEY` | Not set |
| `PATENTSVIEW_API_KEY` | Not set |
| `SEMANTIC_SCHOLAR_API_KEY` | Not set (unauthenticated; rate-limited) |

## Pilot results

| Ticker | sec | products | hiring | research | patents | earnings |
|--------|-----|----------|--------|----------|---------|----------|
| MSFT | success (15) | success (8) | no_results | success (10) | api_key_missing | api_key_missing |
| GOOGL | success (10) | success (9) | success (10) | source_unavailable | api_key_missing | api_key_missing |
| JPM | success (8) | success (10) | success (10) | success (10) | api_key_missing | api_key_missing |

**Run #10:** 100 evidence items, 3 documents, 11 ok / 7 failed in 35.2s

## Validation

```
missing_source_anchor: 0
missing_raw_hash: 0
missing_source_category: 0
duplicate_raw_hash_rows: 0
```

## Notes

- MSFT Google Jobs returned empty after retries (`no_results`); NVDA/GOOGL/JPM hiring worked in earlier Block C runs.
- GOOGL research hit Semantic Scholar rate limit (`source_unavailable`); JPM research succeeded on retry in same run.
- Expected `api_key_missing` for earnings and patents without optional keys.
