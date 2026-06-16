# Phase 1 full validation run summary (Block D Step 4.3)

**Date:** 2026-06-16  
**Command:** `ai-collect collect --validation-set`  
**Run ID:** #11

## Scale

| Metric | Value |
|--------|-------|
| Companies | 35 |
| Evidence items (run) | 971 |
| Evidence items (DB total) | 991 |
| SEC documents | 35 |
| Runtime | 482 s (~8 min) |

## Per-source outcomes (Run #11)

| Collector | success | no_results | api_key_missing | source_unavailable |
|-----------|---------|------------|-----------------|-------------------|
| sec_filings | 35 | — | — | — |
| web_products | 35 | — | — | — |
| hiring_jobs | 28 | 7 | — | — |
| research | 8 | — | — | 27 |
| patents | — | — | 35 | — |
| earnings_calls | — | — | 35 | — |

## Validation

All violation counts **0** after full run.

## Export

```bash
ai-collect export-all --output-dir data/exports/phase1_20260616
```

Files: `companies.csv`, `documents.csv`, `evidence_items.csv`, `evidence_items.jsonl`, `collector_status.csv` (local only).

## API keys at run time

- Set: `SEC_USER_AGENT`, `SERPAPI_API_KEY`
- Missing: `FMP_API_KEY`, `PATENTSVIEW_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY`
