# Vendor evaluation: Lightcast vs SerpAPI Google Jobs

**Status:** draft  
**Date:** 2026-06-19  
**Replaces / competes with:** `serpapi_jobs` (`hiring_jobs` collector)  
**Registry id:** `lightcast` (`phase: 3`, `enabled: false`)

## Summary

**SerpAPI Google Jobs** is our current hiring pillar: cheap per-search billing but
quota-bound, low structured fields, and mixed listing quality (including LinkedIn
scrapes). **Lightcast** (formerly Emsi Burning Glass) offers workforce analytics APIs
with normalized occupation skills data — higher cost, higher structure, better fit if
investors fund premium hiring signal at S&P 500 scale.

**Draft recommendation:** defer Lightcast until SerpAPI quota is restored and pilot
hiring quality is re-measured; then run a 50-ticker head-to-head before approval.

## Evidence quality vs current APIs

| Criterion | SerpAPI Jobs | Lightcast | Notes |
|---|---|---|---|
| Coverage (S&P 500) | Good reach via Google Jobs | Strong US employer coverage; enterprise contract | Lightcast needs API access quote |
| Signal relevance | Keyword match on postings | SOC/ONET skills, posting trends | Lightcast better for workforce analytics narrative |
| False positive rate | Medium (generic ML job ads) | Lower with normalized taxonomy | SerpAPI often captures non-AI roles |
| Historical depth | Snapshot per search | Time series native | Advantage Lightcast |
| Structured fields | Title, snippet, URL | Occupation, skills, geography, trends | Lightcast |

**Pilot baseline (Jun 2026):** SerpAPI hiring 25 success / 21 `source_unavailable` /
7 `no_results` on latest status (pilot-heavy); full S&P refresh blocked by quota.

## Legal / licensing

| | SerpAPI | Lightcast |
|---|---|---|
| Deployment | Internal scoring product — verify SerpAPI ToS for stored results | Enterprise DPA typically required |
| Raw storage | We store `raw_api_responses` today | Confirm contract allows audit retention |
| Redistribution | Likely restricted | Restricted — internal use only |
| Blockers | Quota / search ToS | Contract negotiation lead time |

## Cost at S&P 500 scale

| Item | SerpAPI Jobs | Lightcast (planning) |
|---|---|---|
| Pricing model | Per search (~$0.01 est.) | Licensed API / seat + volume |
| Full S&P 500 run | ~$5 hiring slice of ~$32 9-source run | TBD — registry placeholder $0.25/call |
| Monthly refresh (14d TTL jobs) | ~$10–15/mo at 2×/month | TBD — likely **$500–2k+/mo** at scale |
| vs incumbent | Baseline | Premium — justify with quality + compliance |

See [`data-sources-investor-brief.md`](../../data-sources-investor-brief.md) for investor cost context.

## API stability and limits

| Item | SerpAPI | Lightcast |
|---|---|---|
| Rate limits | Plan search quota (hit Jun 2026) | Contract-tier |
| Uptime | Good; 429 on quota exhaustion | Enterprise SLA typical |
| Auth | API key | API key / OAuth (TBD) |
| Sandbox | Developer plan | Sales-led trial |
| Migration risk | Low (already integrated) | New collector `lightcast_hiring` stub exists |

## Audit / reprocess support

- **SerpAPI:** raw responses stored; not reprocessable (search snapshots).
- **Lightcast:** likely structured JSON suitable for audit; reprocess TBD per endpoint.
- **Adapter complexity:** Lightcast — **medium** (new client, mapping to `job_posting`).

## Overlap

- Duplicates `serpapi_jobs` pillar only.
- Does not replace SerpAPI products/press/docs — those stay on SerpAPI or separate vendors.

## Recommendation

- [ ] Approve for implementation
- [x] **Defer** — restore SerpAPI quota first; run 50-ticker comparison (`--pilot-set`,
  hiring only) with quality rubric from [`phase-1-spot-check.md`](../phase-1-spot-check.md).
- [ ] Reject

**Next steps:** obtain Lightcast trial pricing; add API sample responses to this doc;
if approved, follow §6A.4 (`config/platforms.yaml` → collector → tests → sync docs).
