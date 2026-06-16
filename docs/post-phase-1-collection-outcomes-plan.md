# Post Phase 1 — Collection outcome semantics (implementation plan)

**Status:** Complete (2026-06-16)  
**Depends on:** Phase 1 complete (Blocks A–D)  
**Coding Standards:** §1 (traceability), §2 (collection/scoring boundary), §7 (failure-handling tests), §13 (docs), §14 (definition of done)

**Related docs:**

- Strategic context: [`data-collection-initial-plan.md` §12](data-collection-initial-plan.md#12-collection-status-and-failure-handling)
- Operational rules: [`data-sources.md`](data-sources.md#collection-outcome-semantics)
- Inference rules: [`scoring-methodology.md` §3.2 / §5.1](scoring-methodology.md)
- Progress tracker: [`implementation-plan.md`](implementation-plan.md)

---

## Goal

Make every `(company, collector)` run **audibly explainable**: downstream consumers must
know whether zero evidence means:

1. we **never attempted** the source,
2. we **attempted but failed** (outcome unknown),
3. the **source answered empty** (no material at origin for our query), or
4. the **source had material but our pipeline produced zero evidence rows** (filtered / extracted to zero).

> **Absence of evidence is not evidence of absence.**  
> Only case (3) is a weak signal of “no observable activity in this channel.” Cases (1), (2), and (4) must not be scored as zero AI activity.

---

## Vocabulary (canonical)

### Layer A — `status` (existing, keep)

Defined in `src/evidence_collection/status.py` and recorded in `collector_status.status`.

| `status` | Meaning |
|---|---|
| `success` | Run completed; see counters and `outcome_reason` for detail |
| `no_results` | Run completed with **zero evidence rows inserted** |
| `api_key_missing` | Not attempted — required/optional key absent |
| `api_limit_reached` | Not completed — quota exhausted |
| `source_unavailable` | Attempted — transport/API/parse failure |
| `rate_limited` | Attempted — throttled (e.g. HTTP 429) |
| `parse_failed` | Response received but unusable |
| `company_not_found` | Entity resolution failed (e.g. missing CIK) |
| `ambiguous_company` | Multiple entity matches |
| `skipped` | Registry gate (platform disabled / wrong phase) |

### Layer B — `outcome_reason` (new, required when `status` ∈ {`success`, `no_results`})

Machine-readable sub-reason stored in `collector_status.message` using a **`reason:` prefix**:

```text
reason:source_empty
reason:filtered_to_zero
reason:partial_success
```

| `outcome_reason` | When to use |
|---|---|
| `source_empty` | HTTP/API succeeded; origin returned no rows/documents/transcripts/hits for this company+query |
| `filtered_to_zero` | Origin returned material (or a document was stored) but **zero** evidence rows after filter/extraction |
| `partial_success` | Optional — some evidence inserted but material was truncated (caps, limits) |

**Stability rule:** reason codes are a controlled vocabulary. Add new codes only via this doc + change-log.

Human detail after the code is allowed: `reason:source_empty — google_jobs returned 0 listings`.

### Layer C — operational counters (existing + extended)

Recorded on `CollectorResult` / `collector_status` and optionally `collection_metrics`.

| Field | Meaning |
|---|---|
| `evidence_count` | Rows inserted this run |
| `documents_count` | Documents stored (SEC filing, earnings transcript, …) |
| `api_calls` | HTTP calls made |
| `source_hits` *(new metric)* | Raw items returned by API before filtering |
| `candidates_after_filter` *(new metric)* | Items surviving collector-specific filter |

**Interpretation cheat sheet:**

| `status` | `outcome_reason` | `documents_count` | `source_hits` | Safe inference |
|---|---|---|---|---|
| `success` | — | ≥0 | ≥0 | Evidence exists |
| `no_results` | `source_empty` | 0 | 0 | Source empty for query |
| `no_results` | `filtered_to_zero` | ≥1 **or** `source_hits` ≥1 | ≥1 | **Not** proof of no AI activity |
| `source_unavailable` / `rate_limited` | — | — | — | **Unknown** — exclude pillar |
| `api_key_missing` / `skipped` | — | — | — | **Not measured** — exclude pillar |

---

## Current vs target (Phase 1 baseline)

| Collector | Today (blur) | Target |
|---|---|---|
| `sec_filings` | `no_annual_filing` vs doc stored + 0 paragraphs both `no_results` | `source_empty` vs `filtered_to_zero`; keep `documents_count` |
| `web_products` | empty API vs AI regex filter → both `no_results` | distinguish via `source_hits` + reason |
| `hiring_jobs` | empty `jobs_results` → `no_results` | `source_empty`; if jobs exist but all dropped → `filtered_to_zero` (future filter) |
| `research` | `[]` vs 429 | `source_empty` vs `rate_limited` (already partly separated) |
| `patents` | `total_hits=0` vs error | `source_empty` vs `source_unavailable` |
| `earnings_calls` | `no_transcripts` vs empty body vs no AI paragraphs | `source_empty` / skip / `filtered_to_zero` |

---

## Block F — Implementation steps

### Step F.1 — Document & schema design ✅ (this file + doc sync)

**Deliverables:** this plan; updates to §12 initial plan, `data-sources.md`, `scoring-methodology.md`, `implementation-plan.md`, `phase-1-development-plan.md`.

**Done when:**

- [x] Controlled vocabulary published
- [x] Per-collector target table agreed
- [x] Team 2 scoring rules documented (unknown ≠ zero)

**Commit:** `Document collection outcome semantics (post Phase 1 plan)`

---

### Step F.2 — Model + persistence

**Depends on:** F.1

**Modify:**

- `src/evidence_collection/status.py` — add `OutcomeReason` constants (or enum-like class)
- `src/evidence_collection/models.py` — extend `CollectorResult` with optional `source_hits`, `candidates_after_filter`, helper to format `message` as `reason:…`
- `src/evidence_collection/db/repository.py` — `record_status` persists new counters if added to schema
- `src/evidence_collection/db/migrations.py` — optional columns on `collector_status`: `source_hits`, `candidates_after_filter`, `outcome_reason` (or keep reason in `message` only for MVP)

**Design choice (MVP):** store `outcome_reason` in `message` as `reason:code` to avoid migration; add columns in F.2b if querying becomes painful.

**Done when:**

- [x] `CollectorResult` carries hit/filter counts
- [x] `record_status` stores them (metrics fallback acceptable for MVP)

**Verify:** unit tests on `CollectorResult` + status formatting

**Commit:** `Add collection outcome reason codes and result counters`

---

### Step F.3 — Collector updates (one PR per collector or one block)

**Depends on:** F.2

**Modify each collector** to set `outcome_reason` and counters:

| Collector | `source_empty` | `filtered_to_zero` |
|---|---|---|
| `sec_filings` | no annual filing | filing stored, 0 AI paragraphs |
| `web_products` | `organic_results` empty | results > 0, AI filter → 0 |
| `hiring_jobs` | `jobs_results` empty after retries | (future) post-filter zero |
| `research` | `data: []` | papers returned but title empty / all skipped |
| `patents` | `total_hits == 0` | hits > 0 but none inserted (edge) |
| `earnings_calls` | no transcript in lookback | transcript stored, 0 AI paragraphs |

**Done when:**

- [x] Each Phase 1 collector sets `reason:…` on every `success` / `no_results`
- [x] `documents_count` / `source_hits` populated where applicable

**Verify:** unit tests with mocked API payloads for each reason path

**Commit:** `Populate outcome_reason across Phase 1 collectors`

---

### Step F.4 — CLI & reporting

**Depends on:** F.3

**Modify:**

- `ai-collect status` — show `outcome_reason` column (parse from message or column)
- `ai-collect validate-company` — include last reason per source
- `quality_report()` — optional breakdown: count runs by `outcome_reason`
- Export CSVs include reason when present

**Done when:**

- [x] `ai-collect status --ticker MSFT` shows reason for `no_results` rows
- [x] QA can distinguish MSFT hiring `source_empty` vs SEC `filtered_to_zero`

**Verify:** manual spot-check on validation set

**Commit:** `Expose collection outcome_reason in status and validate-company`

---

### Step F.5 — Inference layer guardrails (Team 2)

**Depends on:** F.3

**Modify:**

- `src/inference/` scoring — when aggregating pillar counts, **exclude** pillars where last status ∈ `{api_key_missing, skipped, source_unavailable, rate_limited, parse_failed}`
- **Do not treat** `no_results` + `filtered_to_zero` as “zero activity”
- Document weight redistribution when pillar is unknown (e.g. skip vs neutral)

**Done when:**

- [x] Scoring tests cover: unknown status → pillar excluded, not zero
- [x] `scoring-methodology.md` matches behavior

**Verify:** `pytest tests/unit/test_scoring.py`

**Commit:** `Score only measured pillars; treat unknown outcomes as missing data`

---

### Step F.6 — Validation sample re-run & QA

**Depends on:** F.4, F.5

**Run:**

```bash
ai-collect collect --validation-set
ai-collect status
python -c "
import sqlite3; c=sqlite3.connect('data/evidence.sqlite')
for row in c.execute('''
  SELECT status, message, COUNT(*) FROM collector_status
  WHERE run_id=(SELECT MAX(id) FROM collector_runs)
  GROUP BY status, message ORDER BY 1,2
'''): print(row)
"
```

**Done when:**

- [x] Validation set run has `reason:` on all `success` / `no_results` rows
- [x] QA note appended to `docs/qa/phase-1-spot-check.md` or new `docs/qa/outcome-semantics-validation.md`
- [x] `pytest` passes

**Commit:** `Validate outcome semantics on 35-company sample`

---

## Testing requirements (Coding Standards §7)

Each collector needs tests for:

- `api_key_missing` path (where applicable)
- `source_unavailable` / `rate_limited` path
- `source_empty` → `no_results` + `reason:source_empty`
- `filtered_to_zero` → `no_results` + `reason:filtered_to_zero` + non-zero `documents_count` or `source_hits`
- `success` with evidence > 0

Use mocked HTTP — no live API in unit tests for reason classification.

---

## Definition of done (Block F complete)

- [x] All steps F.1–F.6 checked off
- [x] `change-log.md` updated
- [x] `implementation-plan.md` Block F marked complete
- [x] No scoring change without `scoring-methodology.md` update
- [x] `pytest` green; validation set manually spot-checked

---

## Progress tracker

```text
Block F — Collection outcome semantics
  [x] F.1  Document & schema design
  [x] F.2  Model + persistence
  [x] F.3  Collector updates
  [x] F.4  CLI & reporting
  [x] F.5  Inference guardrails
  [x] F.6  Validation re-run & QA
```

---

*Last updated: 2026-06-16 — Block F implemented + audit clean; 150 tests.*
