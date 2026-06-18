# Implementation Plan (current)

Concise, living **status tracker** (Coding Standards §13). Detailed step-by-step
guides live in the phase documents below — not duplicated here.

**Platform registry (live):** [`config/platforms.yaml`](../config/platforms.yaml)  
**Strategic context:** [`data-collection-initial-plan.md`](data-collection-initial-plan.md) · [§6A platforms](data-collection-initial-plan.md#6a-data-platform-decisions)

---

## Documentation map

| Phase | Status | Step-by-step / reference |
|---|---|---|
| Phase 1 | Complete | [`phase-1-development-plan.md`](phase-1-development-plan.md) |
| Block F (outcomes) | Complete | [`data-sources.md` § outcomes](data-sources.md#collection-outcome-semantics) |
| Phase 2 | Complete | [`phase-2-implementation.md`](phase-2-implementation.md) |
| Phase 3 | In progress | [`phase-3-development-plan.md`](phase-3-development-plan.md) |
| Phase 4 | Planned | [`data-collection-initial-plan.md` § Phase 4](data-collection-initial-plan.md) |

**Required docs (§13):** [`project-control.md`](project-control.md) · [`data-sources.md`](data-sources.md) · [`scoring-methodology.md`](scoring-methodology.md) · [`change-log.md`](change-log.md) · [`setup.md`](setup.md)

---

## Status

- [x] **Phase 0 — Refactor:** evidence/document schema, collector runs/status, raw-response preservation, exports.
- [x] **Phase 0.5 — Standards alignment:** source-quality fields, test/fixture structure.
- [x] **Audit remediation:** validation gate (§22), dedup (§13), `validate` + `reprocess`, versioned scores.
- [x] **Phase 1 — Core collectors + validation sample:** Blocks A–D. **35 companies, 991 evidence rows, 0 validate violations (2026-06-16).**
- [x] **Block F — Collection outcome semantics:** `reason:source_empty` / `filtered_to_zero` / failure vocabulary; scoring guardrails (`v0_2+`). **150 tests.**
- [x] **Phase 2 — On-demand scoring + new sources:** 2.0 ad-hoc scoring, 2.1 GitHub, 2.2 press, 2.3 product docs; `ai_adoption_score_v0_5`. **208 tests (2026-06-16).**
- [ ] **Phase 3 — Scale (in progress):** 3A.1–3A.4 done; pilot export + retries; **3A.5 stale refresh next** → [`phase-3-development-plan.md`](phase-3-development-plan.md)
- [ ] **Phase 4 — Production handoff:** versioned snapshots, field-definition docs, coverage reports.

---

## Phase summaries

### Phase 2 (complete)

| Block | Topic |
|---|---|
| 2.0 | On-demand scoring — `score/run --company`, `resolve`, SEC auto-upsert |
| 2.1 | GitHub repositories |
| 2.2 | Press releases (SerpAPI) |
| 2.3 | Product documentation (SerpAPI + fetch + `reprocess`) |

Details: [`phase-2-implementation.md`](phase-2-implementation.md)

### Phase 3 (planned)

| Track | Focus |
|---|---|
| 3A | Full S&P 500 scale, API costs, incremental refresh, freshness, retry queue |
| 3B | Premium vendor evaluation (`lightcast`, `alphasense`, `revelio`) |

Details: [`phase-3-development-plan.md`](phase-3-development-plan.md)

---

## Team 2 deliverables (tracked)

| Item | Status |
|---|---|
| `signals` table + producer | Planned — interim scorer uses evidence counts |
| Versioned scoring formula | Done — `ai_adoption_score_v0_5` (nine pillars) |
| Read API over evidence corpus | Phase 4 |

See [`scoring-methodology.md`](scoring-methodology.md).
