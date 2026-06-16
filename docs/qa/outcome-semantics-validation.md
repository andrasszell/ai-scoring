# Outcome semantics validation (Block F)

**Date:** 2026-06-16  
**Run:** `#12` — `ai-collect collect --validation-set` (35 tickers, ~248s)

## Validation gate

```text
ai-collect validate
  missing_outcome_reason: 0  (latest status per ticker/source only)
  total evidence: 1061 rows / 35 companies
```

## Run #12 outcome mix

| status | outcome_reason | count |
|---|---|---:|
| success | (none — evidence present) | 106 |
| no_results | source_empty | 7 |
| api_key_missing | — | 70 |
| source_unavailable | — | 27 |

All **7** `no_results` rows in run #12 carry `reason:source_empty` (hiring_jobs for
BAC, INTC, LLY, MSFT, PLTR, TSLA, UNH — Google Jobs returned no listings).

No `filtered_to_zero` rows in this run (no company had a stored document or API hits
with zero AI keyword paragraphs after Block F re-collect).

## Spot-check: MSFT (`ai-collect status --ticker MSFT`)

| source | status | reason | hits | interpretation |
|---|---|---|---:|---|
| sec_annual_filing | success | — | 1 | 15 AI paragraphs from 10-K |
| web_search_product | success | — | 8 | 8 product hits |
| job_posting | no_results | **source_empty** | 0 | Jobs engine empty — not proof of no hiring |
| earnings_call_transcript | api_key_missing | — | — | pillar excluded from score |
| patent | api_key_missing | — | — | pillar excluded from score |
| research_paper | source_unavailable | — | — | pillar excluded from score |

This matches the Block F goal: MSFT hiring `source_empty` is audibly distinct from
SEC `success` with evidence and from `api_key_missing` / `source_unavailable` (unknown).

## CLI samples

```bash
ai-collect status --ticker MSFT
ai-collect validate-company MSFT
ai-collect validate   # outcome breakdown + missing_outcome_reason gate
```

## Notes

- `quality_report()` audits **latest** status per `(ticker, source_type)` so legacy
  pre–Block F runs do not fail `missing_outcome_reason`.
- Inference formula bumped to `ai_adoption_score_v0_2` — unmeasured/failed pillars
  excluded; weights redistributed across measured pillars only.
