# Phase 3 — Step-by-Step Development Plan

**Team 1 — Evidence Discovery Layer**

Use this document as the **implementation checklist for Phase 3**. Phase 2 is
complete — see [`phase-2-implementation.md`](phase-2-implementation.md).

Phase 3 has **two tracks** that can proceed in parallel after prerequisites:

| Track | Goal | Primary deliverable |
|---|---|---|
| **3A — Scale** | Run and maintain collection for the **full S&P 500** | Refreshable evidence database with cost and freshness controls |
| **3B — Premium vendors** | Evaluate and optionally wire **licensed** data platforms | Approved collector(s) in registry, or documented rejections |

**Related docs:**

| Doc | Role |
|---|---|
| [`data-collection-initial-plan.md`](data-collection-initial-plan.md) | Strategic context — [§Phase 3 scale](data-collection-initial-plan.md), [§6A.1 evaluation criteria](data-collection-initial-plan.md#6a1-evidence-source-platforms-phase-1--approved) |
| [`implementation-plan.md`](implementation-plan.md) | Living status checkboxes |
| [`config/platforms.yaml`](../config/platforms.yaml) | Phase 3 stubs: `lightcast`, `alphasense`, `revelio` (`enabled: false`) |
| [`data-sources.md`](data-sources.md) | Operational platform tables |

---

## Phase 3 goals (from strategic plan)

### 3A — Scale to full company universe

```text
Run collection for full S&P 500 (~500 tickers × 9 collectors)
Track API costs per run / per source
Handle rate limits gracefully (backoff, partial runs)
Incremental refresh (only stale tickers / sources)
Data freshness monitoring (alert when corpus is old)
Failed-source retry queue (re-run source_unavailable / rate_limited)
```

**Deliverable:** refreshable S&P 500 AI evidence database with operational metrics.

### 3B — Premium or licensed sources (evaluate first)

Candidates in registry (disabled) or strategic plan:

| Registry ID | Vendor | Replaces / complements |
|---|---|---|
| `lightcast` | Lightcast | SerpAPI jobs (`hiring_jobs`) |
| `alphasense` | AlphaSense | FMP earnings transcripts |
| `revelio` | Revelio Labs | Workforce / hiring analytics |

Additional candidates **not yet in YAML:** Coresignal, Proxycurl, LinkedIn Talent
Insights, FactSet, PitchBook, CB Insights, Similarweb, BuiltWith.

**Rule:** no premium vendor is enabled until [§6A.1 evaluation criteria](data-collection-initial-plan.md#6a1-evidence-source-platforms-phase-1--approved) are documented (quality, legal, cost at S&P scale, API stability, audit/reprocess).

---

## Prerequisites (before Phase 3A)

- [x] Phase 2 complete — 9 collectors, `ai_adoption_score_v0_5`, 188 tests.
- [ ] Full S&P 500 loads cleanly: `ai-collect load-companies` (no CIK gaps for index tickers).
- [ ] API keys provisioned for paid pillars you intend to run at scale (`SERPAPI_API_KEY`, `FMP_API_KEY`, etc.).
- [ ] Entity metadata seeded for scale: expand `company_domains.yaml` and `company_github_orgs.yaml` beyond validation set.
- [ ] Baseline cost estimate: one full validation-set collect with API call counts from `collector_status.api_calls`.

---

## How to use this plan

```text
1. Pick a step (3A or 3B track).
2. Implement only that step.
3. Run Verify commands.
4. Mark [x] here and in implementation-plan.md.
5. change-log.md entry for operational or architectural decisions.
```

**Rules:**

- One step = one focused PR when possible.
- Do not enable Phase 3 platforms in YAML until collector + tests exist.
- Scoring formula changes require a new `ai_adoption_score_v0_N` version.
- Collection never imports scoring (Coding Standards §2).

---

## Block 3A — Scale and operations

### Step 3A.1 — Full S&P 500 universe load verification

**Goal:** Confirm `load-companies` produces ~500 rows with CIK, sector, and domains where configured.

**Files:** `src/evidence_collection/universe/`, `config/company_domains.yaml`

**Done when:**

- [ ] `ai-collect load-companies` completes without error.
- [ ] `SELECT COUNT(*) FROM companies` ≥ 490 (allow Wikipedia/SEC merge gaps).
- [ ] Spot-check 10 tickers: CIK present, `website_domain` where expected.

**Verify:**

```bash
ai-collect load-companies
sqlite3 data/evidence.sqlite "SELECT COUNT(*) FROM companies;"
ai-collect validate-company MSFT JPM XOM
```

---

### Step 3A.2 — Full S&P 500 collection pilot (subset first)

**Goal:** Run all 9 collectors on a **50-ticker pilot** before full index.

**Done when:**

- [ ] `ai-collect collect --limit 50` (or explicit ticker list) completes.
- [ ] `ai-collect validate` → 0 violations, `missing_outcome_reason` = 0.
- [ ] Export bundle captured for review.

**Verify:**

```bash
ai-collect collect --limit 50
ai-collect validate
ai-collect export-all --output-dir data/exports/phase3_pilot_YYYYMMDD
```

---

### Step 3A.3 — API cost tracking

**Goal:** Persist per-run and per-(ticker, source) API cost estimates.

**Proposed design:**

- Extend `collection_metrics` or new `api_cost_events` table.
- Each collector reports `api_calls` (already on `collector_status`).
- Map platform `cost_model` + call counts to estimated USD (config table, not hardcoded in collectors).
- CLI: `ai-collect status --costs` or export column in run summary.

**Files (TBD):** `src/evidence_collection/runner.py`, `db/migrations.py`, `config/api_cost_estimates.yaml`

**Done when:**

- [ ] Pilot run produces per-source call totals.
- [ ] Documented cost estimate for full S&P × 9 collectors.
- [ ] Tests for metric persistence.

---

### Step 3A.4 — Rate-limit resilience

**Goal:** Partial runs survive `rate_limited` / `source_unavailable` without aborting (already per-collector); add **retry scheduling** metadata.

**Done when:**

- [ ] Failed statuses queryable: `SELECT … WHERE status IN ('rate_limited','source_unavailable')`.
- [ ] Documented backoff policy per vendor (GitHub, SerpAPI, SEC, Semantic Scholar).
- [ ] Optional: `ai-collect retry-failed` command (re-run only failed ticker×source pairs).

---

### Step 3A.5 — Incremental refresh

**Goal:** Re-collect only stale companies or sources.

**Proposed design:**

- `collector_status.created_at` + configurable TTL per `source_type`.
- `ai-collect collect --stale-days 30` or `--since DATE`.
- Skip fresh (ticker, source) pairs unless `--force`.

**Done when:**

- [ ] Second collect on same tickers skips fresh sources (or only runs stale).
- [ ] Tests with fixture timestamps.

---

### Step 3A.6 — Freshness monitoring

**Goal:** Report corpus age and coverage gaps.

**Deliverables:**

- `ai-collect freshness` — per-ticker oldest evidence, per-source last success.
- Export suitable for dashboard / cron alert.

**Done when:**

- [ ] Command lists tickers with no evidence in N days.
- [ ] Documented SLA targets (e.g. SEC quarterly, jobs monthly).

---

### Step 3A.7 — Full S&P 500 production collect

**Goal:** One documented full-universe run.

**Done when:**

- [ ] `ai-collect load-companies && ai-collect collect --all` completes.
- [ ] `ai-collect validate` = 0 violations.
- [ ] QA sample: manual spot-check per [`docs/qa/`](qa/).
- [ ] Export + cost report archived.

**Deliverable:** `data/exports/phase3_sp500_YYYYMMDD/`

---

## Block 3B — Premium vendor evaluation

### Step 3B.1 — Evaluation template

**Goal:** One markdown evaluation per candidate vendor.

**Create:** `docs/qa/vendor-evaluations/{vendor}.md` using criteria from §6A.1:

```text
Evidence quality vs Phase 1/2 APIs
Legal / licensing for our deployment
Cost at S&P 500 scale × refresh frequency
API stability, rate limits, historical coverage
Audit / reprocess support
```

**Done when:**

- [ ] Template committed.
- [ ] At least one candidate (recommend: Lightcast vs SerpAPI jobs) has draft evaluation.

---

### Step 3B.2 — Pilot one premium collector (if approved)

**Goal:** Implement **one** Phase 3 platform end-to-end (example: `lightcast`).

**Follow §6A.4:**

```text
config/platforms.yaml → collector → tests → enabled: true → docs → validate
```

**Done when:**

- [ ] Collector returns Block F outcome reasons.
- [ ] Disabled by default until evaluation sign-off.
- [ ] Scoring pillar decision documented (new version if added).

**Do not start** until 3B.1 evaluation is approved.

---

## Phase 3 success criteria

| Criterion | Target |
|---|---|
| Universe | Full S&P 500 in `companies` |
| Collectors | 9 Phase 1+2 sources run at scale (± approved Phase 3 vendors) |
| Quality gate | `ai-collect validate` = 0 violations |
| Operations | Cost visibility + incremental refresh + freshness report |
| Reproducibility | Versioned exports + migration history |

---

## Out of scope (Phase 3)

- Production read API (Phase 4).
- `signals` table / LLM extraction (Team 2 roadmap).
- Sector-adjusted scoring percentiles.
- Automatic scheduling / cron (document commands; deploy separately).

---

## Quick reference (planned commands)

```bash
# Scale (as implemented in 3A)
ai-collect load-companies
ai-collect collect --all
ai-collect collect --stale-days 30      # planned 3A.5
ai-collect retry-failed                 # planned 3A.4
ai-collect freshness                    # planned 3A.6

# Premium (as implemented in 3B)
ai-collect show-platforms --phase 3
ai-collect collect --source lightcast --ticker MSFT   # when enabled
```

---

*Update this plan as steps complete. Mirror status in [`implementation-plan.md`](implementation-plan.md).*
