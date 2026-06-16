# On-demand company scoring (any company, not only S&P 500)

**Status:** Partially available (Phase 1); polish planned before / alongside Phase 2  
**Coding Standards:** §1 traceability, §2 collection/scoring boundary, §13 docs

**Related:** [`data-collection-initial-plan.md`](data-collection-initial-plan.md) (entity resolution),
[`scoring-methodology.md`](scoring-methodology.md), [`implementation-plan.md`](implementation-plan.md).

---

## Goal

Score **any investigable public company**, not only S&P 500 constituents:

1. User provides a **company name or ticker** (e.g. `Microsoft`, `MSFT`, `Elanco Animal Health`).
2. System **resolves identity** (ticker, CIK, legal name, optional domain/aliases).
3. System **collects evidence** across enabled Phase 1 sources.
4. System **computes and explains** the AI Depth Score.

**S&P 500 remains the primary bulk universe** (Phase 3 scale). On-demand scoring is
the **optional path** for one-off names, mid-caps, recent IPOs, and validation tickers
outside the index (e.g. ELAN).

---

## Company universes (three tiers)

| Tier | How loaded | Typical use |
|---|---|---|
| **S&P 500** | `ai-collect load-companies` (Wikipedia + SEC CIK merge) | Bulk runs, default mega-caps, Phase 3 full index |
| **Validation / custom list** | `config/validation_companies.yaml` + SEC fallback | QA, sector spreads, non-index filers |
| **Ad-hoc (on-demand)** | `ai-collect analyze "<name>"` → SEC `company_tickers.json` fallback | Single company by name or ticker |

Collectors use **ticker + company_name + CIK + aliases + website_domain** — not
membership in the S&P 500 table. Once a company row exists in `companies`, collection
and scoring behave the same as for index names.

---

## What works today (Phase 1)

### End-to-end workflow (two commands)

```bash
# 1. Resolve by name, upsert company row, collect all enabled sources
ai-collect analyze "Microsoft"
ai-collect analyze MSFT
ai-collect analyze "Elanco Animal Health"    # non-S&P: SEC filer fallback

# 2. Score from the evidence corpus (ticker required today)
ai-score score --ticker MSFT --persist
ai-score export-scores --ticker MSFT --output data/exports/msft_score.csv
```

`analyze`:

- Matches loaded DB first (exact ticker/name → prefix → substring).
- If no match, searches **all SEC filers** via `company_tickers.json`.
- Upserts the resolved company, applies domains/aliases from config when present.
- Runs the same collectors as `collect` for that single company.

`ai-score score`:

- Reads `evidence_items` + latest `collector_status` for the ticker.
- Applies `ai_adoption_score_v0_2` (excludes unmeasured/failed pillars).
- Requires evidence rows to exist (run `analyze` or `collect` first).

### Limits today

| Limit | Detail |
|---|---|
| **Scoring input** | `ai-score` accepts **`--ticker` only**, not free-text company name |
| **`collect --ticker X`** | Skips tickers **not already in DB**; use `analyze` to add ad-hoc names |
| **Coverage** | Best for **US SEC filers** (10-K/CIK). Web/hiring/patents/research use name/ticker; private or non-US names may have sparse SEC pillar |
| **One-shot CLI** | No single `ai-score --company "…"` that collects + scores yet |

---

## Phase 2 deliverables (on-demand polish)

Tracked in [`implementation-plan.md`](implementation-plan.md) § Phase 2.0.

| # | Task | Done |
|---|---|---|
| 2.0.1 | Document ad-hoc workflow (this file) + README / methodology FAQ | [x] |
| 2.0.2 | **`ai-score score --company "Name"`** — resolve name/ticker (shared `match_rows` / SEC fallback), score if evidence exists; clear error if not collected | [ ] |
| 2.0.3 | **`ai-score run --company "Name"`** (or `--collect`) — optional one-shot: resolve → collect if stale/missing → score → print explanation | [ ] |
| 2.0.4 | **`ai-collect collect --ticker X`** — auto-upsert from SEC when ticker missing from DB (same as analyze, non-interactive) | [ ] |
| 2.0.5 | **`ai-collect resolve "Name"`** — print resolved ticker/CIK/name without collecting (dry-run for scripts) | [ ] |
| 2.0.6 | Tests: non-S&P SEC filer (e.g. ELAN), ambiguous name rejection, score-by-name with fixture evidence | [ ] |

**Design rules:**

- Collection stays in `ai-collect`; scoring stays in `ai-score` (§2 boundary).
- A convenience `run` command may **orchestrate** both CLIs internally but must not
  merge scoring logic into collectors.
- Resolved companies are **persisted** in `companies` for reproducibility.

---

## Out of scope (explicit)

- **Private companies** with no public filings — web/hiring may return partial evidence;
  SEC pillar will be empty or `company_not_found`.
- **Non-US listings** without SEC CIK — not supported for regulatory filing pillar;
  other pillars may still run on name match (quality varies).
- **Automatic S&P-only restriction** — we do not enforce index membership anywhere in code.

---

## Quick reference

```bash
# Ad-hoc today
ai-collect analyze "Company Name Or TICKER"
ai-score score --ticker TICKER --persist

# Bulk S&P (primary)
ai-collect load-companies
ai-collect collect --all

# After Phase 2.0 (planned)
ai-score score --company "Company Name"
ai-score run --company "Company Name" --persist
```
