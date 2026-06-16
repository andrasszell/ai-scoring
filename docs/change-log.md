# Change Log

Important changes and decisions (Coding Standards §13). Newest first.

## 2026-06-16 — Phase 1 Step 1.1: platform registry YAML

- Added `config/platforms.yaml`: 2 universe loaders, 6 Phase 1 platforms (enabled),
  Phase 2/3 stubs (disabled). Step-by-step plan in `phase-1-development-plan.md`.

## 2026-06-16 — Platform registry planned (§6A.4)

- Added **§6A.4 Platform registry** to the initial plan: `config/platforms.yaml`
  as the single editable list of approved platforms; schema, consumers, and
  five-step change workflow for adding sources reliably.
- Expanded **Phase 1** in both plans: registry implementation is the first task
  block before collector stabilization and 25–50 company validation.
- Updated `implementation-plan.md` with detailed Phase 1 checklist (registry,
  collectors, validation sample).
- Updated `data-sources.md` to defer to registry once implemented.

## 2026-06-16 — Data platform decisions documented (§6A)

- Added **§6A Data Platform Decisions** to `data-collection-initial-plan.md`:
  Phase 1 approved source platforms (universe + six collectors), MVP storage
  stack (SQLite + local raw files), scale triggers, and Team 1 → Team 2 handoff.
- Aligned `data-sources.md` as the operational companion to §6A.
- Updated §14 and §16 to cross-reference §6A; corrected §14 table list to match
  the implemented schema.
- Renamed strategic plan file to `data-collection-initial-plan.md`.

## 2026-06-16 — Standards-compliance fixes (audit remediation)

Closed the gaps found in the strict standards audit:

- **§22 blocker fixed:** evidence insertion now validates every row and **rejects
  any without a source URL or date** (and without traceability fields). New
  `validation.py` + tests.
- **§13 dedup implemented:** evidence deduped by `raw_hash` (per ticker+collector),
  documents and raw API responses deduped by `content_hash`. Skips are logged. Tests added.
- **§6 per-domain refinement:** evidence on a company's own domain is upgraded to
  `official_company / high` (`sources.refine_for_url`).
- **§14/§18 validation report:** new `ai-collect validate` command (rule violations
  + coverage). New `repository.quality_report`.
- **§1 reproducibility:** new `ai-collect reprocess` re-extracts evidence from stored
  document text with no network calls; earnings transcripts now persist `text_path`.
- **§4/§5 scoring made compliant (interim):** versioned formula
  `ai_adoption_score_v0_1`, `ScoreResult` with a per-driver explanation,
  `input_evidence_ids`, and a persisted `scores` table (migration 3). `ai-score
  score/export-scores --persist`. Scores are append-only (history preserved).
- **Decision:** no `signals` table yet — building it without a producer would be a
  premature abstraction (§15). It is an explicit Team 2 deliverable; the interim
  scorer treats each collector's evidence count as a signal and records
  `input_evidence_ids` in lieu of `input_signal_ids`.
- Test suite: 50 tests.

## 2026-06-16 — Phase 0.5: align to coding standards

- Added source-quality fields to `evidence_items` (migration 2): `raw_hash`,
  `confidence_initial`, `source_category`, `source_reliability`.
- Added `src/evidence_collection/sources.py` source taxonomy + reliability map (§6).
- Added required docs: `project-control.md`, `data-sources.md`, `change-log.md`,
  `setup.md`, `implementation-plan.md`; renamed `METHODOLOGY.md` →
  `scoring-methodology.md`.
- Restructured tests into `tests/unit`, `tests/integration`, `tests/fixtures`;
  added a tiny end-to-end fixture (raw evidence → evidence → score → explanation).
- **Decision:** keep the two-package layout (`evidence_collection` + `inference`)
  as an approved deviation from §3; rationale recorded in `project-control.md`.

## 2026-06-16 — Phase 0: separate collection from scoring

- Refactored the prototype `sp500_ai_depth` into two packages: `evidence_collection`
  (CLI `ai-collect`) and `inference` (CLI `ai-score`). Scoring removed from the
  collection workflow.
- New schema via a lightweight migration runner: `companies`, `company_aliases`,
  `documents`, `evidence_items`, `raw_api_responses`, `collector_runs`,
  `collector_status`, `collection_metrics`.
- Standardized evidence (§8) and document (§9) objects; added collector versioning,
  structured status taxonomy, structured logging, and raw-response preservation.
- Dropped pillar classification and AI-count metrics from collection (interpretation
  moved to the inference layer).
- New exporters: `companies/documents/evidence_items/collector_status` CSV + JSONL.
- Rewrote the test suite for the new structure (36 tests).
