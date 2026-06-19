# Phase 4 — Production handoff (in progress)

**Goal:** Versioned, documented evidence corpus ready for the inference team.

Strategic context: [`data-collection-initial-plan.md`](data-collection-initial-plan.md) § Phase 4.

---

## Step 4.1 — Versioned snapshots

**Goal:** One command produces an export bundle + manifest for Team 2.

**Deliverables:**

- `ai-collect snapshot` — CSV/JSONL exports + `manifest.json` (validate, coverage, schema version).
- [`evidence-field-definitions.md`](evidence-field-definitions.md) — frozen field reference.

**Done when:**

- [x] `ai-collect snapshot` writes manifest with row counts and validation summary.
- [x] Field definitions documented.
- [x] Snapshot of Phase 3 S&P corpus archived with tag `phase3_sp500`.

**Verify:**

```bash
ai-collect snapshot --tag phase3_sp500 --output-dir data/exports/snapshots/corpus_phase3_sp500
```

**Archived:** `data/exports/snapshots/corpus_phase3_sp500/` (2026-06-19).

---

## Step 4.2 — Source coverage report

**Goal:** Machine-readable coverage beyond `ai-collect freshness`.

**Deliverables:**

- Extend snapshot manifest or add `ai-collect coverage` with per-pillar gaps.

**Done when:**

- [ ] Report lists tickers missing each `source_type` at S&P scale.

---

## Step 4.3 — Parquet export (optional)

**Goal:** Analytics-friendly format for warehouse load.

**Done when:**

- [ ] `ai-collect export-evidence --format parquet` or snapshot includes `.parquet`.

---

## Out of scope (Phase 4)

- Read-only HTTP API (optional later).
- Automatic scheduling / cron deployment.

---

## Quick reference

```bash
ai-collect snapshot                              # default: data/exports/snapshots/corpus_YYYYMMDD
ai-collect snapshot --tag phase3_sp500 -o data/exports/snapshots/corpus_phase3_sp500
ai-collect validate
```
