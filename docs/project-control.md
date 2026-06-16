# Project Control

Current scope, non-goals, and architecture for the AI Adoption Intelligence Platform.
This is the top-level control document referenced by the Coding Standards (§13).

| Document | Role |
|---|---|
| [`phase-1-development-plan.md`](phase-1-development-plan.md) | **Step-by-step Phase 1 checklist** (implement in order) |
| [`post-phase-1-collection-outcomes-plan.md`](post-phase-1-collection-outcomes-plan.md) | **Block F** — source empty vs filtered-to-zero vs failure |
| [`data-collection-initial-plan.md`](data-collection-initial-plan.md) | Team 1 strategic plan; **§6A = platforms**, **§6A.4 = registry**, **§12 = status** |
| [`implementation-plan.md`](implementation-plan.md) | Current progress; Phase 1 task checklist |
| [`project-control.md`](project-control.md) | Scope, non-goals, architecture decisions |
| [`data-sources.md`](data-sources.md) | Operational detail; synced from registry (Phase 1) |
| [`scoring-methodology.md`](scoring-methodology.md) | Inference-layer scoring (Team 2) |
| [`change-log.md`](change-log.md) | Important decisions and changes |

## Architecture

Two layers with a strict separation of duties (Coding Standards §2):

| Layer | Package | CLI | Owns |
|---|---|---|---|
| Evidence Discovery (Team 1) | `src/evidence_collection` | `ai-collect` | find, retrieve, normalize, preserve evidence |
| Inference (Team 2) | `src/inference` | `ai-score` | signals, confidence, scoring, explanation |

The collection layer **never scores**. The inference layer **never fetches**.

## Folder-layout deviation (approved)

The Coding Standards §3 suggest a single-package layout
(`/src/collection`, `/processing`, `/scoring`, `/models`, `/storage`, `/cli`).

We deliberately deviate to **two installable packages** instead, because:

- the two packages map 1:1 to the two teams and ship two separate console
  scripts (`ai-collect`, `ai-score`);
- it makes the "collection must not import scoring" boundary enforceable at the
  package level, not just by convention.

The standard's *intent* (clear collection / processing / scoring / storage / cli
separation) is preserved via modules inside each package:

```
src/evidence_collection/
  collectors/   # source connectors (≈ /collection)
  extraction.py # text → candidate evidence (≈ /processing)
  db/           # connection, migrations, repository (≈ /storage)
  models.py     # shared dataclasses (≈ /models)
  sources.py    # source taxonomy + reliability (§6)
  cli.py        # entry point (≈ /cli)
src/inference/
  scoring.py    # formulas, weights (≈ /scoring)
  cli.py
```

## Scope (now)

- Phase 0 (done): separate collection from scoring; standardized evidence/document
  schema; collector runs/status; raw-response preservation; clean exports.
- Phase 0.5 (in progress): align to Coding Standards — source quality fields,
  required docs, test/fixture structure.
- Phase 1 (next): stabilize the 6 core collectors; validate 25–50 companies.

## Non-goals (collection layer)

- final AI adoption score, weighting models, uncertainty/sensitivity analysis;
- interpreting strategic meaning beyond candidate-evidence extraction;
- premium/licensed sources (Phase 3 evaluation only).

## Three invariants every change must preserve (Coding Standards §1)

1. **Evidence traceability** — every evidence item links to a source URL/date,
   a stored document, a `raw_hash`, and the collector name+version.
2. **Scoring explainability** — scores derive only from visible signals + named,
   versioned formulas (inference layer).
3. **Reproducibility** — migrations + preserved raw responses let another developer
   reproduce the corpus.
