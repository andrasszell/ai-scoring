# Phase 1 — Step-by-Step Development Plan

**Team 1 — Evidence Discovery Layer**

Use this document as your **implementation checklist**. Complete one step at a
time; do not start the next step until the current step’s **Done when** criteria
are met. Each step ends with a suggested git commit message.

**Related docs:**

| Doc | Role |
|---|---|
| [`data-collection-initial-plan.md`](data-collection-initial-plan.md) | Strategy, §6A platform decisions, §6A.4 registry design |
| [`implementation-plan.md`](implementation-plan.md) | High-level Phase 1 status (update checkboxes as you finish blocks) |
| [`data-sources.md`](data-sources.md) | Synced from registry after Step 1.8 |

**Phase 1 deliverables:**

1. `config/platforms.yaml` — single editable list of all platforms (live + planned).
2. Collectors stable: source dates, entity data, validation passing.
3. Evidence corpus for **25–50 companies** with `ai-collect validate` = 0 violations.
4. Export bundle + short QA note for Team 2.

---

## How to use this plan

```text
1. Read the step (goal, files, acceptance criteria).
2. Implement only that step — no drive-by refactors.
3. Run the Verify commands.
4. Mark the step [x] in this file (or in implementation-plan.md).
5. Commit (suggested message provided).
6. Move to the next step.
```

**Rules:**

- One step = one focused PR or commit when possible.
- If a step fails verification, fix before continuing.
- Do not add Phase 2 collectors in Phase 1 — only register them as `enabled: false`.
- `.env` secrets never go in git.

---

## Prerequisites (before Step 1.1)

- [ ] Repo cloned; `pip install -e ".[dev]"` works.
- [ ] `.env` has at least `SEC_USER_AGENT` set.
- [ ] `pytest` passes (baseline: 50 tests).
- [ ] You can run: `ai-collect init-db && ai-collect collect --ticker MSFT --source sec`.

---

## Block A — Platform registry (Steps 1.1–1.8)

*Goal: one YAML file drives which platforms exist, whether they run, and their metadata.*

### Step 1.1 — Create `config/platforms.yaml` (static data only) ✅

**Depends on:** Prerequisites

**Goal:** Add the registry file with every Phase 1 platform + universe loaders.
No Python changes yet.

**Create:**

- `config/platforms.yaml`

**Include:**

| Section | Entries |
|---|---|
| `loaders` | `wikipedia_sp500`, `sec_company_tickers` |
| `platforms` | `sec_edgar`, `fmp_transcripts`, `serpapi_web`, `serpapi_jobs`, `patentsview`, `semantic_scholar` |
| `platforms` (disabled) | 2–3 Phase 2 placeholders (`phase: 2`, `enabled: false`, e.g. `github`, `press_releases`) |
| `platforms` (disabled) | 2–3 Phase 3 placeholders (`phase: 3`, `enabled: false`, e.g. `lightcast`, `alphasense`) |

**Field reference:** see [§6A.4](data-collection-initial-plan.md#6a4-platform-registry-single-source-of-truth) in the initial plan.

**Map collector names to existing code:**

| Registry `collector` | Existing `Collector.name` |
|---|---|
| `sec_filings` | `sec_filings` |
| `earnings_calls` | `earnings_calls` |
| `web_products` | `web_products` |
| `hiring_jobs` | `hiring_jobs` |
| `patents` | `patents` |
| `research` | `research` |

**Done when:**

- [x] YAML parses without error.
- [x] All 6 active collectors + 2 loaders documented with `phase: 1`, `enabled: true`.
- [x] Phase 2/3 entries present but `enabled: false`.

**Verify:** Manual review of YAML against §6A.1 tables in initial plan.

**Commit:** `Add config/platforms.yaml with Phase 1 platform registry entries`

---

### Step 1.2 — Platform loader module + dataclasses ✅

**Depends on:** Step 1.1

**Goal:** Load and validate registry at runtime.

**Create:**

- `src/evidence_collection/platforms.py`

**Implement:**

- `Platform` and `Loader` dataclasses (frozen)
- `load_registry(path: Path | None = None) -> Registry` — default path `config/platforms.yaml` relative to project root or env `PLATFORMS_YAML`
- Validation rules:
  - Required fields present per §6A.4 schema
  - Unique `id` values
  - `collector` names must match known collectors OR be marked `phase >= 2`
  - `source_category` / `source_reliability` in allowed vocabularies
  - `confidence_initial` in 0.0–1.0
- `Registry.platforms_enabled(phase=1) -> list[Platform]`
- `Registry.platform_by_collector(name: str) -> Platform | None`
- `Registry.auth_status(platform) -> "ok" | "missing" | "not_required"` (read env via existing `settings`)

**Modify:**

- `src/evidence_collection/config.py` — optional `platforms_yaml: Path` setting
- `pyproject.toml` — add `pyyaml` dependency

**Done when:**

- [x] `load_registry()` returns typed objects for all entries in YAML.
- [x] Invalid YAML (missing field, duplicate id) raises clear `ValueError`.

**Verify:**

```bash
python -c "
from evidence_collection.platforms import load_registry
r = load_registry()
assert len(r.platforms_enabled()) >= 6
print('ok', [p.id for p in r.platforms_enabled()])
"
```

**Commit:** `Add platform registry loader with schema validation`

---

### Step 1.3 — Unit tests for registry loader ✅

**Depends on:** Step 1.2

**Goal:** Lock registry behavior before wiring collectors.

**Create:**

- `tests/unit/test_platforms.py`
- `tests/fixtures/platforms_minimal.yaml` (tiny valid fixture)
- `tests/fixtures/platforms_invalid.yaml` (one deliberate error)

**Test cases:**

- Loads minimal fixture successfully
- Rejects duplicate `id`
- Rejects missing required field
- `platforms_enabled()` excludes `enabled: false`
- `platforms_enabled(phase=1)` excludes phase 2/3
- `auth_status` returns `missing` when env key empty and `required: true`

**Done when:**

- [x] `pytest tests/unit/test_platforms.py -q` passes.
- [x] Full suite still passes.

**Verify:** `pytest -q`

**Commit:** `Add unit tests for platform registry loader`

---

### Step 1.4 — Wire `sources.py` to registry ✅

**Depends on:** Step 1.3

**Goal:** Evidence reliability metadata comes from registry, not hardcoded dict.

**Modify:**

- `src/evidence_collection/sources.py` — `profile_for(source_type)` looks up registry first; keep `_PROFILES` as fallback if registry unavailable (or remove fallback once stable)
- `src/evidence_collection/collectors/base.py` — no change if `profile_for` already used in `make_evidence`

**Done when:**

- [x] `make_evidence` sets `source_category`, `source_reliability`, `confidence_initial` from registry values for SEC filings.
- [x] Existing tests pass (`test_serpapi`, `test_end_to_end`).

**Verify:** `pytest tests/unit/test_serpapi.py tests/integration/test_end_to_end.py -q`

**Commit:** `Load source reliability defaults from platform registry`

---

### Step 1.5 — Wire collector enablement + env-key checks to registry ✅

**Depends on:** Step 1.4

**Goal:** `collect` respects `enabled: false` and registry auth rules.

**Modify:**

- `src/evidence_collection/collectors/__init__.py` — `get_collectors()` filters by registry (`enabled`, `phase==1`)
- Each collector OR `runner.py` — before collect, check registry auth; return `CollectorResult(API_KEY_MISSING)` from registry metadata (not hardcoded strings)
- Map registry `collector` field → `Collector` instance

**Done when:**

- [x] Setting `enabled: false` for `web_products` in YAML causes `collect --source products` to skip it with status `skipped` or not offer it.
- [x] Missing `SERPAPI_API_KEY` still yields `api_key_missing` with message from registry.

**Verify:**

```bash
# Temporarily set enabled: false for one platform in YAML, then:
ai-collect collect --ticker MSFT --source products
ai-collect status --ticker MSFT
# Revert enabled: true after test
pytest -q
```

**Commit:** `Filter collectors and auth checks via platform registry`

---

### Step 1.6 — Add `ai-collect show-platforms` command ✅

**Depends on:** Step 1.5

**Goal:** Human-readable view of registry + runtime key status.

**Modify:**

- `src/evidence_collection/cli.py` — new subcommand `show-platforms`
  - Columns: `id`, `collector`, `phase`, `enabled`, `vendor`, `env_key`, `key_status`, `cost_model`
  - Optional: `--phase 1`, `--all` (include disabled)

**Done when:**

- [x] `ai-collect show-platforms` runs without DB initialization.
- [x] Output matches `config/platforms.yaml` entries.
- [x] Shows `missing` for unset optional keys.

**Verify:**

```bash
ai-collect show-platforms
ai-collect show-platforms --all
```

**Commit:** `Add ai-collect show-platforms command`

---

### Step 1.7 — Register Phase 2/3 placeholders + collector `platform_id` ✅

**Depends on:** Step 1.6

**Goal:** Collectors declare their registry `id`; adding future sources is YAML-only until adapter exists.

**Modify:**

- `src/evidence_collection/collectors/base.py` — optional `platform_id: str` class attribute matching YAML `id`
- Each collector class — set `platform_id` matching registry
- `config/platforms.yaml` — ensure Phase 2/3 stubs exist

**Done when:**

- [x] Every active collector has matching `platform_id` in YAML and code.
- [x] `show-platforms --all` lists Phase 2/3 entries as disabled.

**Verify:** `ai-collect show-platforms --all | head -20`

**Commit:** `Link collectors to registry platform ids; add Phase 2/3 stubs`

---

### Step 1.8 — Sync docs from registry ✅

**Depends on:** Step 1.7

**Goal:** Docs no longer independently list platforms.

**Modify:**

- `docs/data-sources.md` — add note at top: tables synced from `config/platforms.yaml` on `<date>`; list platforms from registry (manual sync OK for Phase 1; optional script `scripts/sync_platform_docs.py` if you want automation)
- `docs/change-log.md` — entry: registry implemented
- `docs/implementation-plan.md` — mark Block A tasks 1.1–1.8 done

**Optional create:**

- `scripts/sync_platform_docs.py` — reads YAML, prints markdown table (nice-to-have, not required)

**Done when:**

- [x] `data-sources.md` platform table matches YAML.
- [x] §6A.1 in initial plan references registry as live SSOT (not “planned”).

**Verify:** Diff YAML vs data-sources.md manually.

**Commit:** `Sync data-sources doc from platform registry; mark Block A complete`

---

### Block B — Entity metadata (Steps 2.1–2.3) ✅

*Goal: better company identity so collectors and source refinement work reliably.*

### Step 2.1 — Backfill `companies.website_domain` ✅

**Depends on:** Block A complete (or at least Step 1.2)

**Goal:** Enable per-domain source refinement (`official_company` upgrade).

**Modify:**

- `src/evidence_collection/universe/sp500.py` or new `universe/domains.py` — derive domain from known mappings or simple heuristic (e.g. `{ticker: domain}` seed table for Phase 1 mega-caps)
- `src/evidence_collection/db/repository.py` — upsert preserves `website_domain`
- Migration optional if column already exists

**Create (optional):**

- `config/company_domains.yaml` — ticker → domain seed list (keep out of platforms.yaml)

**Done when:**

- [x] After `load-companies`, at least DEFAULT_TICKERS (10) have `website_domain` set.
- [x] `web_products` evidence for MSFT on `microsoft.com` gets `source_category=official_company` (existing test extended).

**Verify:**

```bash
ai-collect load-companies
python -c "
import sqlite3; c=sqlite3.connect('data/evidence.sqlite'); c.row_factory=sqlite3.Row
for r in c.execute('SELECT ticker, website_domain FROM companies WHERE website_domain IS NOT NULL LIMIT 5'):
    print(dict(r))
"
pytest tests/unit/test_serpapi.py -q
```

**Commit:** `Seed companies.website_domain for default universe`

---

### Step 2.2 — Seed `company_aliases` table ✅

**Depends on:** Step 2.1

**Goal:** Move brand aliases from code into DB.

**Modify:**

- `src/evidence_collection/universe/entity.py` — `search_name()` checks `company_aliases` table first, then falls back to `QUERY_ALIASES`
- `src/evidence_collection/cli.py` — on `load-companies`, call alias seeder

**Create:**

- `config/company_aliases.yaml` — ticker → list of `{alias, alias_type}` (e.g. GOOGL → Google, brand)

**Migrate:**

- Move `QUERY_ALIASES` from `entity.py` into YAML; keep tiny code fallback only if DB empty.

**Done when:**

- [x] `company_aliases` populated for GOOGL, META, AMZN at minimum.
- [x] Hiring/products queries use alias from DB (unit test).

**Verify:** `pytest tests/unit/test_entity.py -q`

**Commit:** `Seed company_aliases from config; use DB in search_name`

---

### Step 2.3 — CLI `validate-company` (optional but recommended) ✅

**Depends on:** Step 2.2

**Goal:** Inspect one company’s identity before collecting.

**Modify:**

- `src/evidence_collection/cli.py` — `validate-company MSFT` prints: name, CIK, sector, website_domain, aliases, last collection status per source

**Done when:**

- [x] Command runs and shows sensible output for a loaded ticker.

**Verify:** `ai-collect validate-company MSFT`

**Commit:** `Add ai-collect validate-company command`

---

## Block C — Collector stabilization (Steps 3.1–3.5)

*Goal: every evidence row has source dates where the API provides them; collectors stay idempotent.*

### Step 3.1 — Audit `source_date` coverage

**Depends on:** Block B (recommended)

**Goal:** Know which collectors still emit NULL dates.

**Run:**

```bash
ai-collect collect --ticker MSFT --source sec products hiring patents research
python -c "
import sqlite3; c=sqlite3.connect('data/evidence.sqlite')
for row in c.execute('''
  SELECT collector_name,
         SUM(CASE WHEN source_date IS NULL OR source_date=\"\" THEN 1 ELSE 0 END) as missing,
         COUNT(*) as total
  FROM evidence_items WHERE ticker=\"MSFT\" GROUP BY collector_name
'''):
    print(row)
"
```

**Document findings** in this file or a scratch note.

**Done when:**

- [ ] You have a list of collectors needing date fixes.

**Commit:** none (audit only) — or doc commit: `Document source_date audit for Phase 1`

---

### Step 3.2 — Fix `source_date` for SerpAPI collectors

**Depends on:** Step 3.1

**Modify:**

- `src/evidence_collection/collectors/serpapi.py`
  - Products: use result date/snippet metadata if present; else use collection date as `source_date` (document: “retrieval date used when origin date unknown”) — **must satisfy validation** (URL OR date required; URL already present)
  - Jobs: parse `posted_at` / similar from Google Jobs payload if available; else retrieval date

**Done when:**

- [ ] New MSFT product/job evidence rows have non-null `source_date`.
- [ ] `ai-collect validate` → `missing_source_anchor: 0`.

**Verify:** collect + validate + pytest

**Commit:** `Populate source_date for SerpAPI product and hiring evidence`

---

### Step 3.3 — Fix `source_date` for patents and research

**Depends on:** Step 3.2

**Modify:**

- `src/evidence_collection/collectors/patents.py` — use `patent_date`
- `src/evidence_collection/collectors/research.py` — use paper `year` (already partial)

**Done when:**

- [ ] Patent and research rows have `source_date` populated on re-collect.

**Verify:** `ai-collect collect --ticker MSFT --source patents research && ai-collect validate`

**Commit:** `Populate source_date for patent and research evidence`

---

### Step 3.4 — Earnings collector hardening

**Depends on:** Step 3.3

**Modify:**

- `src/evidence_collection/collectors/earnings.py` — ensure transcript date always set; improve skip when FMP returns empty (clear `no_results` status, not generic error)

**Done when:**

- [ ] With valid `FMP_API_KEY`, at least one transcript stores date + text_path.
- [ ] Without key, status is `api_key_missing` from registry path.

**Verify:** collect with/without key; `ai-collect status`

**Commit:** `Harden earnings collector status and transcript dates`

---

### Step 3.5 — Reprocess smoke test after collector changes

**Depends on:** Step 3.4

**Goal:** Confirm offline reprocess still works after date/metadata changes.

**Verify:**

```bash
ai-collect collect --ticker NVDA --source sec
ai-collect reprocess --source sec --ticker NVDA
ai-collect validate
pytest tests/integration/test_reprocess.py -q
```

**Done when:**

- [ ] Reprocess evidence count matches sec-only collect (approximately).
- [ ] All tests pass.

**Commit:** `Verify reprocess idempotency after Phase 1 collector updates`

---

## Block D — Validation sample (Steps 4.1–4.6)

*Goal: prove the pipeline at modest scale.*

### Step 4.1 — Define validation company set

**Depends on:** Blocks A–C complete

**Create:**

- `config/validation_companies.yaml` — list of 25–50 tickers with notes (sector spread)

**Suggested composition:**

- 10 DEFAULT_TICKERS (mega-cap)
- 10 additional large-cap across sectors (health, finance, energy, consumer)
- 5 mid-cap with known AI activity
- Optional: 5 non-S&P names via SEC fallback (e.g. Elanco) to test entity resolution

**Done when:**

- [ ] YAML list reviewed and approved by you.
- [ ] All tickers exist after `ai-collect load-companies` OR documented SEC fallback path.

**Commit:** `Add validation company list for Phase 1 sample`

---

### Step 4.2 — Pilot collection (3 companies, all sources)

**Depends on:** Step 4.1

**Run:**

```bash
ai-collect load-companies
ai-collect collect --ticker MSFT GOOGL JPM   # no --source = all enabled
ai-collect validate
ai-collect status
```

**Done when:**

- [ ] `validate` shows 0 violations.
- [ ] Status shows expected mix of success / api_key_missing / no_results (document which keys you have).

**Fix loop:** If violations > 0, go back to Block C — do not proceed.

**Commit:** none or `Phase 1 pilot collection notes` if you save logs under `docs/qa/`

---

### Step 4.3 — Full validation run (25–50 companies)

**Depends on:** Step 4.2 clean

**Run:**

```bash
# Load tickers from config/validation_companies.yaml (manual or small script)
ai-collect collect --ticker <list from yaml>
ai-collect validate
ai-collect export-all --output-dir data/exports/phase1_$(date +%Y%m%d)
ai-collect show-platforms
```

**Track:**

- Runtime, API call counts (from `collection_metrics` table)
- Per-source success rate from `collector_status`

**Done when:**

- [ ] 25–50 companies have evidence in DB.
- [ ] `validate` → all violation counts 0.
- [ ] Export bundle saved.

**Commit:** `Phase 1 validation corpus collected for N companies` (do not commit `data/` — exports stay local)

---

### Step 4.4 — QA spot-check template

**Depends on:** Step 4.3

**Create:**

- `docs/qa/phase-1-spot-check.md`

**Include for 5 sample companies (1 page each):**

- Ticker, sector
- Evidence count per collector
- 2–3 manually reviewed evidence rows (URL opens, text plausible, date sane)
- Any false positives from keyword matching?
- Collector status anomalies

**Done when:**

- [ ] Template filled for at least 5 companies.

**Commit:** `Add Phase 1 QA spot-check notes`

---

### Step 4.5 — Phase 1 completion review

**Depends on:** Step 4.4

**Checklist:**

- [ ] `config/platforms.yaml` is SSOT; `show-platforms` works
- [ ] `data-sources.md` synced
- [ ] `pytest` passes
- [ ] `ai-collect validate` = 0 violations on validation set
- [ ] Export bundle ready for Team 2
- [ ] `implementation-plan.md` Phase 1 marked complete
- [ ] `change-log.md` updated

**Verify:**

```bash
pytest -q
ai-collect validate
ai-collect show-platforms
git status   # no .env, no data/*.sqlite committed
```

**Commit:** `Complete Phase 1: platform registry, stabilized collectors, validation sample`

---

## Block E — After Phase 1 (do not start yet)

These are Phase 2 starters — listed so you know where Phase 1 ends:

1. Add Phase 2 platform row to YAML (`enabled: false` → develop → `enabled: true`).
2. Implement new collector adapter.
3. Follow §6A.4 five-step workflow.
4. Expand validation set.

---

## Quick reference — commands per block

| Block | Primary commands |
|---|---|
| A | `pytest tests/unit/test_platforms.py`, `ai-collect show-platforms` |
| B | `ai-collect load-companies`, `ai-collect validate-company MSFT` |
| C | `ai-collect collect`, `ai-collect validate`, `ai-collect reprocess` |
| D | `ai-collect collect --ticker …`, `ai-collect export-all`, `ai-collect validate` |

---

## Progress tracker

Copy this to your working notes and tick as you go:

```text
Block A — Platform registry
  [x] 1.1  platforms.yaml
  [x] 1.2  loader module
  [x] 1.3  loader tests
  [x] 1.4  sources.py wired
  [x] 1.5  collector enablement
  [x] 1.6  show-platforms CLI
  [x] 1.7  platform_id on collectors
  [x] 1.8  docs synced

Block B — Entity metadata
  [x] 2.1  website_domain
  [x] 2.2  company_aliases
  [x] 2.3  validate-company CLI

Block C — Collector stabilization
  [ ] 3.1  source_date audit
  [ ] 3.2  SerpAPI dates
  [ ] 3.3  patents/research dates
  [ ] 3.4  earnings hardening
  [ ] 3.5  reprocess smoke test

Block D — Validation sample
  [ ] 4.1  validation company list
  [ ] 4.2  pilot 3 companies
  [ ] 4.3  full 25–50 run
  [ ] 4.4  QA spot-check
  [ ] 4.5  completion review
```

---

*Last updated: 2026-06-16 — Phase 1 planning*
