# Change Log

Important changes and decisions (Coding Standards §13). Newest first.

## 2026-06-18 — Phase 3A.7: full S&P 500 production runbook

- **`scripts/phase3_sp500_run.sh`** — load, collect `--all`, validate, costs, freshness,
  optional `retry-failed`, export (`PHASE=collect|post` for resume).
- QA: [`qa/phase-3-sp500-run.md`](qa/phase-3-sp500-run.md).
- Collect started 2026-06-18 (`data/exports/phase3_sp500_20260618/`).

## 2026-06-18 — Phase 3A.6: freshness monitoring (`ai-collect freshness`)

- **`ai-collect freshness`** — per-ticker evidence age, per-source last collection vs SLA.
- **`src/evidence_collection/freshness_report.py`** — report builder + JSON export.
- Flags: `--stale-days`, `--stale-only`, `--json`, `--output`, `--fail-on-stale` (cron).
- SLA targets from [`config/source_freshness_ttl.yaml`](../config/source_freshness_ttl.yaml).
- **230 tests.**

## 2026-06-18 — Phase 3A.5: incremental refresh (`--stale-days`)

- **`ai-collect collect --stale-days N`** and **`--since YYYY-MM-DD`** skip fresh
  ticker×source pairs; **`--force`** overrides.
- **`config/source_freshness_ttl.yaml`** — per-`source_type` TTL defaults.
- **`src/evidence_collection/freshness.py`** — policy + planning; runner records `skipped`.
- **221 tests.**

## 2026-06-16 — Phase 3A pilot closed (3A.1–3A.4)

- Pilot collect 50/50 tickers; validate 0 violations; export `phase3_pilot_20260616/`.
- Research 50/50 after Semantic Scholar key fix; `retry-failed` for SerpAPI/product_docs.
- Prerequisites and test counts synced (208). QA: [`qa/phase-3-pilot-run.md`](qa/phase-3-pilot-run.md).
- **Next:** 3A.6 `ai-collect freshness` report.

## 2026-06-16 — Phase 3A.4: retry-failed command

- **`ai-collect retry-failed`** — re-run latest `rate_limited` / `source_unavailable` /
  `api_limit_reached` pairs; `--dry-run`, `--source`, `--ticker` filters.
- **`src/evidence_collection/retry.py`**, `run_targeted_collection()` in `runner.py`,
  `repo.failed_status_rows()`.
- Backoff/retry policy documented in [`data-sources.md`](data-sources.md#rate-limits-and-retry-phase-3a4).
- **208 tests.**

## 2026-06-16 — Phase 3A started: pilot set, universe verify, API cost tracking

- **`config/phase3_pilot_companies.yaml`** — 50-ticker pilot corpus (validation 35 + 15).
- **`config/api_cost_estimates.yaml`** — USD-per-call estimates for cost reporting.
- **CLI:** `ai-collect verify-universe` (3A.1), `collect/load-companies --pilot-set`,
  `ai-collect costs [--run-id] [--project-full-sp500]`.
- **`src/evidence_collection/costs.py`** — summarize run API costs from `collector_status.api_calls`.
- **Entity metadata:** expanded `company_domains.yaml` (+15) and `company_github_orgs.yaml` (+5).
- **201 tests.**

## 2026-06-16 — Documentation consolidation

- **Merged** `on-demand-company-scoring.md` → [`phase-2-implementation.md`](phase-2-implementation.md) § 2.0 (deleted redundant file).
- **Merged** `post-phase-1-collection-outcomes-plan.md` → [`data-sources.md`](data-sources.md) § Collection outcome semantics (deleted redundant file).
- **Slimmed** [`implementation-plan.md`](implementation-plan.md) to status tracker only (no duplicate task tables).
- **Reorganized** [`project-control.md`](project-control.md) as documentation index.
- **Moved** vision notes to [`reference/`](reference/); QA index at [`qa/README.md`](qa/README.md).

## 2026-06-16 — Phase 2 and Phase 3 documentation

- **`phase-2-implementation.md`** — authoritative Phase 2 reference (2.0–2.3 complete).
- **`phase-3-development-plan.md`** — step-by-step Phase 3 checklist (3A scale, 3B premium).
- **`implementation-plan.md`** — links to phase guides; Phase 2/3 summary sections.
- **`project-control.md`**, **`phase-2-implementation.md`**, **`data-sources.md`**, README — cross-links.

## 2026-06-16 — Phase 2.3: product documentation collector

- **`ProductDocsCollector`** — SerpAPI discovers on-domain doc pages; fetches HTML,
  stores text for `reprocess`; AI paragraph extraction (Block F outcomes).
- Requires `website_domain` (from `company_domains.yaml`).
- **`reprocess --source product_docs`** wired via `DOCUMENT_SOURCES`.
- **Scoring** — `ai_adoption_score_v0_5` adds `product_docs` pillar (weight 10).
  **188 tests.**

## 2026-06-16 — Phase 2.2: press releases collector

- **`PressReleasesCollector`** — SerpAPI Google web search for AI-related press
  releases; `site:{website_domain}` when known; Block F outcome reasons.
- **`platforms.yaml`** — `press_releases` enabled (`phase: 2`, `SERPAPI_API_KEY`).
- **Scoring** — `ai_adoption_score_v0_4` adds `press_releases` pillar (weight 8;
  `web_products` 15→10, `hiring_jobs` 15→12). **180 tests.**

## 2026-06-16 — Phase 2.1: GitHub repositories collector

- **`GitHubReposCollector`** — searches configured org slugs via GitHub Search API;
  AI keyword filter on name/description/topics; Block F outcome reasons.
- **`config/company_github_orgs.yaml`** — ticker → GitHub org slug list (entity metadata).
- **`platforms.yaml`** — `github_repos` enabled (`phase: 2`).
- **Registry gate** — all `enabled: true` platforms run by default (not only phase 1).
- **Scoring** — `ai_adoption_score_v0_3` adds `github_repos` pillar (weight 10;
  `web_products` reduced 25→15). **173 tests.**

## 2026-06-16 — Phase 2.0: on-demand company scoring (implemented)

- **`universe/lookup.py`** — shared `lookup_company`, `ensure_single_company`, SEC ticker upsert.
- **`ai-collect resolve`** — identity lookup without collection.
- **`collect --ticker`** — auto-upsert missing tickers from SEC filers.
- **`ai-score score --company`**, **`ai-score run --company`** — resolve + score; `run` orchestrates collection.
- **`inference/company.py`** — scoring-side resolution helpers (collection/scoring boundary preserved).
- Tests: 164 total (`test_universe_lookup`, `test_cli_phase2`, `test_inference_cli_phase2`).

## 2026-06-16 — On-demand company scoring plan (Phase 2.0)

- **Plan (now in [`phase-2-implementation.md`](phase-2-implementation.md) § 2.0):** score
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
- **Plan (now in [`data-sources.md`](data-sources.md#collection-outcome-semantics)):** controlled `outcome_reason` codes (`source_empty`, `filtered_to_zero`), hit counters,
  collector updates (F.2–F.3), CLI (F.4), inference guardrails (F.5).
- **Docs synced:** `data-collection-initial-plan.md` §12, `data-sources.md`,
  `scoring-methodology.md`, `implementation-plan.md`, `phase-1-development-plan.md` Block F,
  `project-control.md`.
- **Status (historical):** plan only at this date; **implemented** in Block F entry above.

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
