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

- [x] Phase 2 complete — 9 collectors, `ai_adoption_score_v0_5`, 208 tests.
- [x] Full S&P 500 loads cleanly: `ai-collect load-companies` (509 companies, all CIK).
- [x] API keys provisioned for scale pillars in use: `SERPAPI_API_KEY`, `FMP_API_KEY`,
  `SEMANTIC_SCHOLAR_API_KEY` ok; `PATENTSVIEW_API_KEY` skipped (API unavailable).
- [x] Entity metadata seeded for **pilot set**: `company_domains.yaml` (51 tickers) + `company_github_orgs.yaml` (23 tickers).
- [x] Baseline cost estimate: pilot collect + `ai-collect costs --project-full-sp500` (~$32/full S&P).

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

- [x] `ai-collect load-companies` completes without error.
- [x] `SELECT COUNT(*) FROM companies` ≥ 490 (509 in DB).
- [x] Spot-check 10 tickers: CIK present, `website_domain` where expected.

**Verify:**

```bash
ai-collect load-companies --pilot-set   # ensure 50 pilot tickers + domains
ai-collect verify-universe              # coverage report + spot-check
ai-collect validate-company MSFT JPM XOM
```

---

### Step 3A.2 — Full S&P 500 collection pilot (50-ticker pilot)

**Goal:** Run all 9 collectors on the **50-ticker pilot** (`config/phase3_pilot_companies.yaml`) before full index.

**Done when:**

- [x] `ai-collect collect --pilot-set` completes.
- [x] `ai-collect validate` → 0 violations, `missing_outcome_reason` = 0.
- [x] Export bundle captured for review.
- [x] `ai-collect costs --project-full-sp500` documents baseline estimate (~$32/full S&P).

**Verify:**

```bash
ai-collect load-companies --pilot-set
ai-collect collect --pilot-set
ai-collect validate
ai-collect costs --project-full-sp500
ai-collect export-all --output-dir data/exports/phase3_pilot_YYYYMMDD
```

---

### Step 3A.3 — API cost tracking

**Goal:** Persist per-run and per-(ticker, source) API cost estimates.

**Proposed design:**

- Extend `collection_metrics` or new `api_cost_events` table.
- Each collector reports `api_calls` (already on `collector_status`).
- Map platform `cost_model` + call counts to estimated USD — [`config/api_cost_estimates.yaml`](../config/api_cost_estimates.yaml).
- CLI: `ai-collect costs [--run-id N] [--project-full-sp500]`; collect summary prints est. USD.

**Files:** `src/evidence_collection/costs.py`, `src/evidence_collection/runner.py`, `config/api_cost_estimates.yaml`

**Done when:**

- [x] Pilot run produces per-source call totals (`ai-collect costs`).
- [x] Documented cost estimate for full S&P × 9 collectors (pilot projection ~$32/run).
- [x] Tests for metric persistence and cost summarization.

---

### Step 3A.4 — Rate-limit resilience

**Goal:** Partial runs survive `rate_limited` / `source_unavailable` without aborting (already per-collector); add **retry scheduling** metadata.

**Done when:**

- [x] Failed statuses queryable: `repo.failed_status_rows()` / `ai-collect retry-failed --dry-run`.
- [x] Documented backoff policy per vendor (GitHub, SerpAPI, SEC, Semantic Scholar) — [`data-sources.md`](data-sources.md#rate-limits-and-retry-phase-3a4).
- [x] `ai-collect retry-failed` command (re-run only failed ticker×source pairs).

---

### Step 3A.5 — Incremental refresh

**Goal:** Re-collect only stale companies or sources.

**Proposed design:**

- `collector_status.created_at` + configurable TTL per `source_type`.
- `ai-collect collect --stale-days 30` or `--since DATE`.
- Skip fresh (ticker, source) pairs unless `--force`.

**Done when:**

- [x] Second collect on same tickers skips fresh sources (or only runs stale).
- [x] Tests with fixture timestamps.

**Verify:**

```bash
ai-collect collect --pilot-set --stale-days 30 --source sec
ai-collect status --ticker MSFT   # fresh sec row shows skipped on re-run
```

---

### Step 3A.6 — Freshness monitoring

**Goal:** Report corpus age and coverage gaps.

**Deliverables:**

- `ai-collect freshness` — per-ticker oldest evidence, per-source last success.
- Export suitable for dashboard / cron alert.

**Done when:**

- [x] Command lists tickers with no evidence in N days.
- [x] Documented SLA targets (e.g. SEC quarterly, jobs monthly).

**Verify:**

```bash
ai-collect freshness --pilot-set
ai-collect freshness --pilot-set --stale-only --fail-on-stale
ai-collect freshness --json --output data/exports/freshness.json
```

---

### Step 3A.7 — Full S&P 500 production collect

**Goal:** One documented full-universe run.

**Runbook:** [`scripts/phase3_sp500_run.sh`](../scripts/phase3_sp500_run.sh) · QA: [`qa/phase-3-sp500-run.md`](qa/phase-3-sp500-run.md)

**Done when:**

- [x] `ai-collect load-companies && ai-collect collect --all` completes.
- [x] `ai-collect validate` = 0 violations.
- [ ] QA sample: manual spot-check per [`docs/qa/`](qa/).
- [x] Export + cost report archived.

**Deliverable:** `data/exports/phase3_sp500_YYYYMMDD/` → [`qa/phase-3-sp500-run.md`](qa/phase-3-sp500-run.md)

**Closed 2026-06-19:** Run #26 — 509 companies, 9,291 evidence rows, 0 validate violations.
Partial SerpAPI/patents (pilot-era); sec + research at full S&P scale.

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

- [x] Template committed.
- [x] At least one candidate (recommend: Lightcast vs SerpAPI jobs) has draft evaluation.

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
ai-collect load-companies --pilot-set
ai-collect verify-universe
ai-collect collect --pilot-set
ai-collect costs --project-full-sp500
ai-collect collect --all
ai-collect collect --stale-days 30      # 3A.5 incremental refresh
ai-collect retry-failed                 # 3A.4 — retry rate_limited / source_unavailable
ai-collect freshness                    # 3A.6 corpus age + SLA report

# Premium (as implemented in 3B)
ai-collect show-platforms --phase 3
ai-collect collect --source lightcast --ticker MSFT   # when enabled
```

---

*Update this plan as steps complete. Mirror status in [`implementation-plan.md`](implementation-plan.md).*
