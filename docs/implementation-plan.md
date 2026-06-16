# Implementation Plan (current)

Concise, living task plan (Coding Standards §13). The original strategic plan is
[`data-collection-initial-plan.md`](data-collection-initial-plan.md); this file
tracks current progress only.

**Platform decisions:** [`data-collection-initial-plan.md` §6A](data-collection-initial-plan.md#6a-data-platform-decisions).
**Platform registry:** [`config/platforms.yaml`](../config/platforms.yaml) — Step 1.1 done; loader in Step 1.2.

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
- [x] **Platform decisions documented:** §6A tables (interim SSOT until registry).
- [ ] **Phase 1 — Stabilize core collectors + platform registry.** Deliverable:
  high-quality evidence corpus for 25–50 companies **and** `config/platforms.yaml`
  as the authoritative platform list.
- [ ] **Phase 2 — High-value sources:** add platforms via registry + new collectors.
- [ ] **Phase 3 — Scale to full universe:** full S&P 500, API-cost tracking,
  incremental refresh, freshness monitoring, failed-source retry queue.
- [ ] **Phase 4 — Productionize handoff:** versioned snapshots, field-definition
  docs, evidence-quality + coverage reports.

---

## Phase 1 — detailed tasks

### 1. Platform registry (first — unblocks reliable source expansion)

| # | Task | Done |
|---|---|---|
| 1.1 | Create `config/platforms.yaml` with schema for all Phase 1 platforms + universe loaders | [x] |
| 1.2 | Add `evidence_collection/platforms.py` — load, validate, expose `Platform` dataclass | [ ] |
| 1.3 | Wire `sources.py` reliability defaults from registry (fallback to code defaults) | [ ] |
| 1.4 | Wire collector enablement + env-key checks from registry | [ ] |
| 1.5 | Add `ai-collect show-platforms` (list id, vendor, phase, enabled, key present/missing) | [ ] |
| 1.6 | Migrate hardcoded platform metadata out of docs/code into YAML | [ ] |
| 1.7 | Tests: schema validation, unknown id rejected, disabled platform skipped | [ ] |
| 1.8 | Document sync rule: edit YAML → sync `data-sources.md` → change-log entry | [ ] |

**Adding a platform after 1.x is complete:**

```text
Edit config/platforms.yaml → collector adapter → tests → sync docs → validate
```

(See §6A.4 in the initial plan.)

### 2. Collector stabilization

| # | Task | Done |
|---|---|---|
| 2.1 | Per-source `source_date` where API provides it (jobs, web, patents, research) | [ ] |
| 2.2 | Populate `companies.website_domain` (enables per-domain source refinement) | [ ] |
| 2.3 | Seed `company_aliases` from in-code brand map + known subsidiaries | [ ] |
| 2.4 | Extend `reprocess` for any new document-backed sources | [ ] |

### 3. Validation sample

| # | Task | Done |
|---|---|---|
| 3.1 | Run full collection for 25–50 companies (default mega-caps + sector spread) | [ ] |
| 3.2 | Capture `ai-collect validate` report (violations must be 0) | [ ] |
| 3.3 | Capture `ai-collect status` + export bundle for Team 2 review | [ ] |
| 3.4 | QA note: sample evidence accuracy per source (manual spot-check) | [ ] |

---

## Team 2 deliverables (tracked, not yet built)

- `signals` table + extraction of typed signals from evidence (§4 derived-signal model).
- Replace the interim count-based scorer; wire `input_signal_ids` (currently
  `input_evidence_ids`), confidence-aware scoring, and sector normalization (§5).
- Scoring tests for signal-driven confidence.

---

## Phase 2 preview (after registry + Phase 1 validation)

Each new source is **one registry row + one collector adapter** — no scattered config.

Planned source families (platform TBD in registry with `phase: 2`, `enabled: false` until approved):

```text
product documentation, developer documentation, technical blogs,
press releases, case studies, GitHub, AI governance pages,
cloud marketplace listings
```

Premium vendors remain `phase: 3`, `enabled: false` until evaluation (§6A.1 criteria).
