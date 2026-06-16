# Implementation Plan (current)

Concise, living task plan (Coding Standards §13). The full strategic plan is in
`Implementation Plan for Data Collection Team.md`; this file tracks the active phase.

## Status

- [x] **Phase 0 — Refactor:** separate collection from scoring; standardized
  evidence/document schema; collector runs/status; raw-response preservation;
  clean exports. (See change-log.)
- [x] **Phase 0.5 — Standards alignment:** source-quality fields + taxonomy,
  required docs, test/fixture structure.
- [x] **Audit remediation:** evidence validation gate (§22), dedup (§13),
  per-domain refinement (§6), `validate` + `reprocess` commands, versioned/explainable
  persisted scores (§4/§5). 50 tests.
- [ ] **Phase 1 — Stabilize core collectors:** improve error handling; per-source
  dates; exact-record dedup; validate 25–50 companies. Deliverable: high-quality
  evidence corpus for 25–50 companies.
- [ ] **Phase 2 — High-value sources:** technical blogs, product/developer docs,
  GitHub, press releases, case studies, AI governance pages, cloud marketplaces.
- [ ] **Phase 3 — Scale to full universe:** full S&P 500, API-cost tracking,
  incremental refresh, freshness monitoring, failed-source retry queue.
- [ ] **Phase 4 — Productionize handoff:** versioned snapshots, field-definition
  docs, evidence-quality + coverage reports.

## Team 2 deliverables (tracked, not yet built — avoid premature abstraction)

- `signals` table + extraction of typed signals from evidence (§4 derived-signal model).
- Replace the interim count-based scorer; wire `input_signal_ids` (currently
  `input_evidence_ids`), confidence-aware scoring, and sector normalization (§5).
- Scoring tests for signal-driven confidence.

## Next concrete steps (Phase 1 candidates)

1. Populate `companies.website_domain` so per-domain refinement actually triggers.
2. Seed `company_aliases` from the in-code brand map + known subsidiaries.
3. Validate a 25–50 company sample; capture the `ai-collect validate` report.
4. Extend `reprocess` coverage as new document sources are added.
