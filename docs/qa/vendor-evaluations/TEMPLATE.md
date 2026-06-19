# Vendor evaluation: {Vendor name}

**Status:** draft | in review | approved | rejected  
**Date:** YYYY-MM-DD  
**Evaluator:**  
**Replaces / competes with:** {existing platform id, e.g. `serpapi_jobs`}  
**Registry id (if approved):** `{vendor_id}` in `config/platforms.yaml`

## Summary

One paragraph: what this vendor provides, why we are evaluating it, and the
recommendation (approve / defer / reject).

## Evidence quality vs current APIs

| Criterion | Current ({incumbent}) | {Vendor} | Notes |
|---|---|---|---|
| Coverage (S&P 500) | | | |
| Signal relevance to AI adoption | | | |
| False positive rate | | | |
| Historical depth | | | |
| Structured fields vs free text | | | |

## Legal / licensing

- Deployment model (internal analytics / redistribution / commercial product):
- Data retention and raw-response storage allowed?
- Attribution requirements:
- Blockers:

## Cost at S&P 500 scale

| Item | Estimate |
|---|---|
| Pricing model | |
| Cost per company per refresh | |
| Cost per full S&P 500 run | |
| Monthly cost at planned refresh cadence | |
| vs incumbent | |

## API stability and limits

| Item | Detail |
|---|---|
| Rate limits | |
| Uptime / SLA | |
| Auth model | |
| Sandbox / trial | |
| Migration risk | |

## Audit / reprocess support

- Raw responses stored? (§9)
- Stable document IDs for reprocess?
- Collector adapter complexity (low / medium / high):

## Overlap with approved platforms

List pillars already covered and whether this vendor duplicates or materially improves them.

## Recommendation

- [ ] Approve for implementation (`enabled: true` in registry)
- [ ] Defer — reason:
- [ ] Reject — reason:

**Next steps if approved:** §6A.4 change workflow (YAML → collector → tests → docs).
