# Implementation Plan (current)

Concise, living task plan (Coding Standards §13). The original strategic plan is
[`data-collection-initial-plan.md`](data-collection-initial-plan.md); this file
tracks current progress only.

**Platform decisions:** [`data-collection-initial-plan.md` §6A](data-collection-initial-plan.md#6a-data-platform-decisions).
**Platform registry (live):** [`config/platforms.yaml`](../config/platforms.yaml).

**Step-by-step implementation guide:** [`phase-1-development-plan.md`](phase-1-development-plan.md)
— use this when coding Phase 1 block-by-block.

**Post Phase 1 (collection outcome semantics):**
[`post-phase-1-collection-outcomes-plan.md`](post-phase-1-collection-outcomes-plan.md)
— distinguish source empty vs filtered-to-zero vs failure (Block F).

---

## Status

- [x] **Phase 0 — Refactor:** separate collection from scoring; standardized
  evidence/document schema; collector runs/status; raw-response preservation;
  clean exports. (See change-log.)
- [x] **Phase 0.5 — Standards alignment:** source-quality fields + taxonomy,
  required docs, test/fixture structure.
- [x] **Audit remediation:** evidence validation gate (§22), dedup (§13),
  per-domain refinement (§6), `validate` + `reprocess` commands, versioned/explainable
  persisted scores (§4/§5). 50 tests.
- [x] **Platform registry (Block A):** `config/platforms.yaml` is the authoritative
  platform list; loader, tests, wired sources/collectors, `show-platforms`, docs synced.
- [x] **Entity metadata (Block B):** `website_domain` + `company_aliases` from config;
  `validate-company` CLI; shared `load_universe()` on all entry points.
- [x] **Phase 1 — Stabilize core collectors + validation sample.** Deliverable:
  high-quality evidence corpus for 25–50 companies (Blocks C–D). **35 companies, 991 evidence rows, 0 validate violations (2026-06-16).**
- [x] **Post Phase 1 — Collection outcome semantics (Block F):** distinguish
  `source_empty` vs `filtered_to_zero` vs failure vs not attempted; expose in
  status/CLI; inference guardrails (`ai_adoption_score_v0_2`). **150 tests (2026-06-16).**
- [ ] **Phase 2 — High-value sources:** add platforms via registry + new collectors.
- [ ] **Phase 2.0 — On-demand company scoring:** score any SEC-listed (or resolved)
  company by name/ticker, not only S&P 500 — see
  [`on-demand-company-scoring.md`](on-demand-company-scoring.md). Partial today via
  `ai-collect analyze` + `ai-score score --ticker`; Phase 2 adds `--company` and optional one-shot `run`.
- [ ] **Phase 3 — Scale to full universe:** full S&P 500, API-cost tracking,
  incremental refresh, freshness monitoring, failed-source retry queue.
- [ ] **Phase 4 — Productionize handoff:** versioned snapshots, field-definition
  docs, evidence-quality + coverage reports.

---

## Phase 1 — detailed tasks

### 1. Platform registry (Block A — complete)

| # | Task | Done |
|---|---|---|
| 1.1 | Create `config/platforms.yaml` with schema for all Phase 1 platforms + universe loaders | [x] |
| 1.2 | Add `evidence_collection/platforms.py` — load, validate, expose `Platform` dataclass | [x] |
| 1.3 | Unit tests for registry loader (`test_platforms.py`, fixtures) | [x] |
| 1.4 | Wire `sources.py` reliability defaults from registry (fallback to code defaults) | [x] |
| 1.5 | Wire collector enablement + env-key checks from registry | [x] |
| 1.6 | Add `ai-collect show-platforms` (list id, vendor, phase, enabled, key status) | [x] |
| 1.7 | Link collectors to registry via `platform_id`; Phase 2/3 stubs in YAML | [x] |
| 1.8 | Sync `data-sources.md` from registry; change-log entry | [x] |

**Adding a platform after Block A:**

```text
Edit config/platforms.yaml → collector adapter → tests → sync docs → validate
```

(See §6A.4 in the initial plan.)

### 2. Entity metadata (Block B — complete)

| # | Task | Done |
|---|---|---|
| B.1 | Seed `companies.website_domain` from config for default universe | [x] |
| B.2 | Seed `company_aliases` from config; use DB in `search_name` | [x] |
| B.3 | Add `ai-collect validate-company` identity inspector | [x] |

### 3. Collector stabilization (Block C — complete)

| # | Task | Done |
|---|---|---|
| C.1 | Per-source `source_date` where API provides it (jobs, web, patents, research) | [x] |
| C.2 | Extend `reprocess` for any new document-backed sources | [x] |

### 4. Validation sample (Block D — complete)

| # | Task | Done |
|---|---|---|
| D.1 | Run full collection for 25–50 companies (default mega-caps + sector spread) | [x] |
| D.2 | Capture `ai-collect validate` report (violations must be 0) | [x] |
| D.3 | Capture `ai-collect status` + export bundle for Team 2 review | [x] |
| D.4 | QA note: sample evidence accuracy per source (manual spot-check) | [x] |

### 5. Post Phase 1 — collection outcome semantics (Block F)

| # | Task | Done |
|---|---|---|
| F.1 | Document vocabulary + per-collector targets | [x] |
| F.2 | `CollectorResult` + persistence for reason codes and hit counters | [x] |
| F.3 | Phase 1 collectors emit `reason:source_empty` / `reason:filtered_to_zero` | [x] |
| F.4 | `status` / `validate-company` / exports show outcome reason | [x] |
| F.5 | Inference layer excludes unknown/not-measured pillars from scoring | [x] |
| F.6 | Re-run validation sample + QA note | [x] |

Step-by-step: [`post-phase-1-collection-outcomes-plan.md`](post-phase-1-collection-outcomes-plan.md).

### 6. On-demand company scoring (Phase 2.0 — planned)

Score companies **outside the default S&P 500 load** or by **free-text name**.
Full plan: [`on-demand-company-scoring.md`](on-demand-company-scoring.md).

| # | Task | Done |
|---|---|---|
| 2.0.1 | Document workflow (ad-hoc vs bulk S&P) | [x] |
| 2.0.2 | `ai-score score --company "Name"` (resolve + score existing evidence) | [ ] |
| 2.0.3 | `ai-score run --company "Name"` (optional collect + score one-shot) | [ ] |
| 2.0.4 | `collect --ticker` auto-upsert from SEC when missing from DB | [ ] |
| 2.0.5 | `ai-collect resolve "Name"` dry-run identity lookup | [ ] |
| 2.0.6 | Tests for non-S&P filer + score-by-name paths | [ ] |

**Phase 1 interim:** `ai-collect analyze "<name>"` then `ai-score score --ticker SYMBOL`.

---

## Team 2 deliverables (tracked, not yet built)

| Item | Status |
|---|---|
| `signals` table + producer | Planned — interim scorer uses evidence counts |
| Versioned scoring formula v0.2+ (outcome-aware pillars) | Done — `ai_adoption_score_v0_2` |
| Read API over evidence corpus | Phase 4 |

See [`scoring-methodology.md`](scoring-methodology.md) and [`project-control.md`](project-control.md).
