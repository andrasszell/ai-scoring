# Project Control

Current scope, non-goals, and architecture for the AI Adoption Intelligence Platform.
Top-level control document (Coding Standards §13).

---

## Documentation index

**Quick start:** [`README.md`](README.md) — one-page map to all docs.

### Required (Coding Standards §13)

| Document | Role |
|---|---|
| [`project-control.md`](project-control.md) | Scope, architecture, this index |
| [`implementation-plan.md`](implementation-plan.md) | **Living status** — what is done / next |
| [`data-sources.md`](data-sources.md) | Platforms, env keys, **outcome semantics**, validation sample |
| [`scoring-methodology.md`](scoring-methodology.md) | Formulas, weights, scoring rules (Team 2) |
| [`change-log.md`](change-log.md) | Decisions and changes |
| [`setup.md`](setup.md) | Install, env, smallest E2E run |

### Phase implementation guides

| Document | Role |
|---|---|
| [`phase-1-development-plan.md`](phase-1-development-plan.md) | Phase 1 checklist (complete — historical) |
| [`phase-2-implementation.md`](phase-2-implementation.md) | **Phase 2 reference** (complete — 2.0–2.3) |
| [`phase-3-development-plan.md`](phase-3-development-plan.md) | Phase 3 checklist (planned) |

### Strategic & reference

| Document | Role |
|---|---|
| [`data-collection-initial-plan.md`](data-collection-initial-plan.md) | Team 1 strategy; **§6A** registry schema; **§6A.4** change workflow |
| [`reference/`](reference/) | Vision / white-paper notes (not implementation guides) |
| [`qa/`](qa/) | Validation run notes and spot-checks (historical) |

---

## Architecture

Two layers with a strict separation of duties (Coding Standards §2):

| Layer | Package | CLI | Owns |
|---|---|---|---|
| Evidence Discovery (Team 1) | `src/evidence_collection` | `ai-collect` | find, retrieve, normalize, preserve evidence |
| Inference (Team 2) | `src/inference` | `ai-score` | signals, confidence, scoring, explanation |

The collection layer **never scores**. The inference layer **never fetches**.

### Folder-layout deviation (approved)

Coding Standards §3 suggest a single-package layout. We use **two installable packages**
(`ai-collect`, `ai-score`) so the collection/scoring boundary is enforceable at the
package level. Module layout preserves the standard's intent — see [`setup.md`](setup.md).

---

## Scope (now)

| Phase | Status | Doc |
|---|---|---|
| 0–1 + Block F | Done | [`phase-1-development-plan.md`](phase-1-development-plan.md) |
| 2.0–2.3 | Done | [`phase-2-implementation.md`](phase-2-implementation.md) |
| 3 | In progress (3A.1–3A.4 done; 3A.5 next) | [`phase-3-development-plan.md`](phase-3-development-plan.md) |
| 4 | Planned | [`data-collection-initial-plan.md`](data-collection-initial-plan.md) |

- **Collectors:** 9 enabled (6 Phase 1 + 3 Phase 2). **208 tests.**
- **Scoring:** `ai_adoption_score_v0_5` (nine pillars).
- **Bulk universe:** S&P 500 via `load-companies` (Phase 3: full refresh at scale).
- **On-demand:** any SEC-listed company by name — Phase 2.0 in [`phase-2-implementation.md`](phase-2-implementation.md).

## Non-goals (collection layer)

- Final score interpretation beyond candidate-evidence extraction.
- Premium/licensed sources without Phase 3B evaluation.
- Automatic scheduling / production API (Phase 4).

## Three invariants (Coding Standards §1)

1. **Evidence traceability** — source URL/date, document, `raw_hash`, collector name+version.
2. **Scoring explainability** — versioned formulas, visible weights, per-pillar explanation.
3. **Reproducibility** — migrations, raw responses, `reprocess` for document-backed sources.
