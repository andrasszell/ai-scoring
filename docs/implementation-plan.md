# Implementation Plan (current)

Concise, living task plan (Coding Standards §13). The original strategic plan is
[`data-collection-initial-plan.md`](data-collection-initial-plan.md); this file
tracks current progress only.

**Platform decisions:** [`data-collection-initial-plan.md` §6A](data-collection-initial-plan.md#6a-data-platform-decisions).
**Platform registry (live):** [`config/platforms.yaml`](../config/platforms.yaml).

**Step-by-step implementation guide:** [`phase-1-development-plan.md`](phase-1-development-plan.md)
— use this when coding Phase 1 block-by-block.

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
- [ ] **Phase 1 — Stabilize core collectors + validation sample.** Deliverable:
  high-quality evidence corpus for 25–50 companies (Blocks B–D).
- [ ] **Phase 2 — High-value sources:** add platforms via registry + new collectors.
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

### 2. Collector stabilization (Block B–C)

| # | Task | Done |
|---|---|---|
| 2.1 | Per-source `source_date` where API provides it (jobs, web, patents, research) | [ ] |
| 2.2 | Populate `companies.website_domain` (enables per-domain source refinement) | [ ] |
| 2.3 | Seed `company_aliases` from in-code brand map + known subsidiaries | [ ] |
| 2.4 | Extend `reprocess` for any new document-backed sources | [ ] |

### 3. Validation sample (Block D)

| # | Task | Done |
|---|---|---|
| 3.1 | Run full collection for 25–50 companies (default mega-caps + sector spread) | [ ] |
| 3.2 | Capture `ai-collect validate` report (violations must be 0) | [ ] |
| 3.3 | Capture `ai-collect status` + export bundle for Team 2 review | [ ] |
| 3.4 | QA note: sample evidence accuracy per source (manual spot-check) | [ ] |

---

## Team 2 deliverables (tracked, not yet built)

| Item | Status |
|---|---|
| `signals` table + producer | Planned — interim scorer uses evidence counts |
| Versioned scoring formula v0.2+ | Planned |
| Read API over evidence corpus | Phase 4 |

See [`scoring-methodology.md`](scoring-methodology.md) and [`project-control.md`](project-control.md).
