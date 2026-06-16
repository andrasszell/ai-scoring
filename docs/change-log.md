# Change Log

Important changes and decisions (Coding Standards §13). Newest first.

## 2026-06-16 — On-demand company scoring plan (Phase 2.0)

- **New plan:** [`on-demand-company-scoring.md`](on-demand-company-scoring.md) — score
  any SEC-listed company by name/ticker; S&P 500 remains bulk default.
- **Phase 1 today:** `ai-collect analyze "<name>"` + `ai-score score --ticker`.
- **Phase 2.0 planned:** `ai-score --company`, one-shot `run`, `collect --ticker` SEC upsert.
- Docs synced: `implementation-plan.md`, `project-control.md`, `scoring-methodology.md`,
  `data-sources.md`, `data-collection-initial-plan.md` §7, README, `phase-1-development-plan.md`.

## 2026-06-16 — Block F audit cleanup

- Docs synced: `data-sources.md`, `scoring-methodology.md` v0_2 worked example,
  `implementation-plan.md` Team 2 tracker.
- `input_evidence_ids` lists measured-pillar evidence only; runner logs
  `storage_message()`; CLI outcome label fixed.
- `http.http_error_status()` for structured 429/rate-limit detection in research.
- Tests: sec/earnings/patents outcome paths, research rate_limited, v0_2 regression,
  E2E status-aware scoring.

## 2026-06-16 — Block F: collection outcome semantics (implemented)

- **`outcomes.py`** — controlled `reason:` vocabulary (`source_empty`, `filtered_to_zero`,
  `partial_success`); parse/format helpers.
- **`CollectorResult`** — `source_hits`, `candidates_after_filter`, `outcome_reason`;
  migration 0004 adds counters to `collector_status`.
- **All Phase 1 collectors** emit reason codes on `no_results` paths; success rows carry hit counts.
- **CLI:** `status` shows HITS + REASON; `validate` shows outcome breakdown;
  `validate-company` shows parsed reason per source.
- **Inference:** `ai_adoption_score_v0_2` excludes unmeasured/failed pillars and
  redistributes weights; flags `filtered_to_zero` as low confidence.
- **QA:** `docs/qa/outcome-semantics-validation.md`.
- Test suite: 150 tests.

## 2026-06-16 — Post Phase 1 plan: collection outcome semantics (Block F)

- **Problem:** `no_results` conflates “source empty” vs “filtered to zero” vs failures;
  scoring must not treat all as “company has no AI.”
- **New plan:** [`post-phase-1-collection-outcomes-plan.md`](post-phase-1-collection-outcomes-plan.md)
  — controlled `outcome_reason` codes (`source_empty`, `filtered_to_zero`), hit counters,
  collector updates (F.2–F.3), CLI (F.4), inference guardrails (F.5).
- **Docs synced:** `data-collection-initial-plan.md` §12, `data-sources.md`,
  `scoring-methodology.md`, `implementation-plan.md`, `phase-1-development-plan.md` Block F,
  `project-control.md`.
- **Status:** F.1 documentation complete; implementation not started.

## 2026-06-16 — Block D audit fixes

- **`collect --validation-set`** rejects conflicting `--ticker` / `--all` / `--limit`.
- **`data-sources.md`** — Phase 1 validation sample section; **`.env.example`** —
  `VALIDATION_COMPANIES_YAML`.
- Tests: validation domain coverage, mocked SEC fallback, CLI conflict checks (124 tests).

## 2026-06-16 — Phase 1 complete (Block D: validation sample)

- **`config/validation_companies.yaml`** — 35-ticker Phase 1 validation corpus (mega-cap,
  sector spread, mid-cap AI, SEC fallback names).
- **`universe/validation.py`** — load validation set; `ensure_validation_companies()` with
  SEC filer fallback for non-S&P tickers (e.g. ELAN).
- **CLI:** `ai-collect collect --validation-set` and `load-companies --validation-set`.
- **`config/company_domains.yaml`** — domains for all validation tickers.
- **QA docs:** `docs/qa/phase-1-pilot-notes.md`, `phase-1-validation-run.md`,
  `phase-1-spot-check.md`.
- **Validation run:** 35 companies, 991 evidence rows, 0 `ai-collect validate` violations;
  export at `data/exports/phase1_20260616/` (local).
- Test suite: 121 tests.

## 2026-06-16 — Phase 1 Block C: source_date stabilization

- **`dates.py`** — shared source-date helpers with `date_provenance` metadata.
- SerpAPI, patents, research, earnings collectors populate `source_date`; earnings hardened.
- Test suite: 114 tests.

## 2026-06-16 — Phase 1 Block B: entity metadata (Steps 2.1–2.3)

- **`config/company_domains.yaml`** — seeds `companies.website_domain` for default tickers.
- **`config/company_aliases.yaml`** — brand aliases seeded into `company_aliases` on load.
- **`universe/domains.py`, `universe/aliases.py`, `universe/load.py`** — shared
  `load_universe()` (domains + aliases) used by `load-companies`, `collect`, and
  `analyze`; `enrich_companies()` backfills domains before collection.
- **`search_name(company, conn=...)`** — DB aliases first; SerpAPI collectors wired.
- **CLI:** `ai-collect validate-company MSFT` — identity + alias + status inspector.
- Test suite: 89 tests.

## 2026-06-16 — Phase 1 Block A: platform registry implemented (Steps 1.2–1.8)

- **Registry loader:** `platforms.py` with schema validation; unit tests in
  `test_platforms.py`.
- **Wired consumers:** `sources.profile_for` reads reliability from YAML;
  `registry_gate` filters collectors by `enabled`/`phase` and auth rules;
  collectors declare `platform_id` matching registry `id`.
- **CLI:** `ai-collect show-platforms [--all] [--phase N]` — no DB required.
- **Docs synced:** `data-sources.md` tables match `config/platforms.yaml`;
  optional `scripts/sync_platform_docs.py` for future sync.
- Test suite: 78 tests.

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
