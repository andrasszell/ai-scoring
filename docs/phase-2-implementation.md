# Phase 2 — Implementation Reference (complete)

**Status:** complete (2026-06-16) · **188 tests**

Phase 2 adds **on-demand company scoring** (any SEC-listed name, not only S&P 500)
and **three new evidence collectors** (GitHub, press releases, product documentation).
This document is the authoritative implementation reference for what was built and how
to operate it.

**Related docs:**

| Doc | Role |
|---|---|
| [`data-sources.md`](data-sources.md) | Platform tables + collection outcome semantics |
| [`scoring-methodology.md`](scoring-methodology.md) | Formula `ai_adoption_score_v0_5` (nine pillars) |
| [`implementation-plan.md`](implementation-plan.md) | High-level status checkboxes |
| [`data-collection-initial-plan.md` §6A.4](data-collection-initial-plan.md#6a4-platform-registry-single-source-of-truth) | Registry change workflow |

---

## Goals and deliverables

| Sub-phase | Goal | Deliverable |
|---|---|---|
| **2.0** | Score companies outside the default S&P load by free-text name | `ai-score score/run --company`, `ai-collect resolve`, SEC auto-upsert on `collect --ticker` |
| **2.1** | Open-source AI activity signal | `GitHubReposCollector` + `company_github_orgs.yaml` |
| **2.2** | Corporate AI announcements | `PressReleasesCollector` (SerpAPI) |
| **2.3** | First-party product/developer docs | `ProductDocsCollector` (SerpAPI discovery + page fetch + `reprocess`) |

**Collection layer after Phase 2:** 9 enabled collectors (6 Phase 1 + 3 Phase 2).

---

## Architecture decisions

### Registry gate (enabled platforms, any phase)

Phase 1 originally ran only `phase: 1` platforms. Phase 2 changed
`registry_gate.collector_gate()` to skip **only** when `enabled: false`. All
`enabled: true` platforms run in default `collect`, regardless of `phase` number.

`enabled_cli_sources()` returns CLI keys for every enabled platform.

### Collection / scoring boundary (unchanged)

- **`ai-collect`** — fetch, normalize, store evidence; never scores.
- **`ai-score`** — read corpus, compute versioned score; never fetches.
- **`ai-score run --company`** orchestrates `run_collection()` then `score_company()`;
  it does not embed scoring logic in collectors.

### Scoring formula evolution

Each new pillar bumped the named formula version (Coding Standards §5):

| Version | Change |
|---|---|
| `ai_adoption_score_v0_2` | Outcome-aware pillar exclusion (Block F) |
| `ai_adoption_score_v0_3` | + `github_repos` (weight 10); `web_products` 25→15 |
| `ai_adoption_score_v0_4` | + `press_releases` (8); `web_products` 15→10, `hiring_jobs` 15→12 |
| **`ai_adoption_score_v0_5`** | + `product_docs` (10); `github_repos` 10→8, `press_releases` 8→7, `web_products` 10→5 |

Current weights (sum = 100): see [`scoring-methodology.md`](scoring-methodology.md).

---

## Collector reference (Phase 2)

| CLI `--source` | Collector `name` | Platform ID | Vendor | Env key | Entity metadata required |
|---|---|---|---|---|---|
| `github` | `github_repos` | `github_repos` | GitHub Search API | `GITHUB_TOKEN` (optional) | `company_github_orgs.yaml` |
| `press` | `press_releases` | `press_releases` | SerpAPI Google web | `SERPAPI_API_KEY` | `website_domain` recommended |
| `product_docs` | `product_docs` | `product_documentation` | SerpAPI + HTTP fetch | `SERPAPI_API_KEY` | **`website_domain` required** |

### Block 2.0 — On-demand company scoring

Score **any investigable public company**, not only S&P 500 constituents. S&P 500
remains the primary **bulk** universe (Phase 3 scale); on-demand is the path for
one-off names, mid-caps, recent IPOs, and validation tickers outside the index
(e.g. ELAN).

**Code:**

- `src/evidence_collection/universe/lookup.py` — `lookup_company`, `ensure_single_company`, `upsert_tickers_from_sec`
- `src/inference/company.py` — `resolve_for_scoring`, `score_resolved_company`, `open_evidence_db`
- `src/evidence_collection/cli.py` — `cmd_resolve`; `collect --ticker` SEC upsert
- `src/inference/cli.py` — `score --company`, `run --company`, `export-scores --company`

#### Company universes (three tiers)

| Tier | How loaded | Typical use |
|---|---|---|
| **S&P 500** | `ai-collect load-companies` (Wikipedia + SEC CIK merge) | Bulk runs, Phase 3 full index |
| **Validation / custom** | `config/validation_companies.yaml` + SEC fallback | QA, sector spreads |
| **Ad-hoc** | `analyze` / `resolve` / SEC `company_tickers.json` fallback | Single company by name |

Collectors use **ticker + company_name + CIK + aliases + website_domain** — not S&P
membership. Once a row exists in `companies`, collection and scoring are identical.

#### End-to-end workflow

```bash
# Collect + score (step by step)
ai-collect analyze "Microsoft"
ai-collect analyze "Elanco Animal Health"    # non-S&P: SEC filer fallback
ai-score score --company "Microsoft" --persist

# One-shot
ai-score run --company "Elanco Animal Health" --persist

# Identity only (no collection)
ai-collect resolve "Microsoft"

# Non-interactive upsert + collect
ai-collect collect --ticker ELAN MSFT
```

| Command | Behavior |
|---|---|
| `analyze` | Resolve → upsert company → collect all enabled sources |
| `resolve` | Resolve identity only (ticker, CIK, name) |
| `collect --ticker X` | Auto-upsert from SEC when ticker missing from DB |
| `score --company` | Resolve + score existing evidence; error if none |
| `run --company` | Collect if no evidence (or `--collect` to refresh), then score |

**Design rules:** collection in `ai-collect`, scoring in `ai-score` (§2). `run`
orchestrates both but does not merge scoring into collectors.

#### Out of scope

- Private companies without SEC filings — SEC pillar empty; other pillars may be partial.
- Non-US listings without CIK — regulatory pillar unsupported.
- No S&P-only restriction in code.

**Verify:**

```bash
ai-collect resolve "Microsoft"
ai-collect collect --ticker ELAN
ai-score run --company "Elanco Animal Health" --persist
pytest tests/unit/test_universe_lookup.py tests/unit/test_cli_phase2.py tests/unit/test_inference_cli_phase2.py -q
```

### Block 2.1 — GitHub repositories

**Code:** `src/evidence_collection/collectors/github_repos.py`

**Flow:**

1. Read org slugs from `config/company_github_orgs.yaml` (max 3 orgs per ticker).
2. GitHub Search API: `org:{slug} (AI terms…)`.
3. Filter repos with `keyword_hits()` on name, description, topics.
4. Outcomes: `source_empty` (no orgs / no hits), `filtered_to_zero`, `rate_limited`.

**Without configured orgs** → `reason:source_empty` (no org-name guessing).

**Verify:**

```bash
ai-collect collect --source github --ticker MSFT NVDA
ai-collect validate-company MSFT    # shows GitHub orgs line
pytest tests/unit/test_github_repos.py tests/unit/test_github_orgs.py -q
```

### Block 2.2 — Press releases

**Code:** `src/evidence_collection/collectors/press_releases.py`

**Flow:**

1. SerpAPI Google search with press-release terms + AI terms.
2. When `website_domain` is set: `site:{domain} …` for first-party press pages.
3. `keyword_hits()` on title + snippet; `refine_for_url()` upgrades on-domain URLs.

**Verify:**

```bash
ai-collect collect --source press --ticker MSFT
pytest tests/unit/test_press_releases.py -q
```

### Block 2.3 — Product documentation

**Code:** `src/evidence_collection/collectors/product_docs.py`

**Flow:**

1. Requires `website_domain`; else `reason:source_empty`.
2. SerpAPI discovers on-domain documentation URLs.
3. Fetches HTML, stores `documents` row + raw/text files under `data/raw/product_docs/`.
4. Extracts AI paragraphs via `candidate_paragraphs()` (same as SEC).
5. Offline re-extract: `ai-collect reprocess --source product_docs`.

**Verify:**

```bash
ai-collect collect --source product_docs --ticker MSFT
ai-collect reprocess --source product_docs --ticker MSFT
pytest tests/unit/test_product_docs.py -q
```

---

## Entity metadata (Phase 2)

Kept **outside** `platforms.yaml` (entity data, not platform approval):

| File | Purpose | Used by |
|---|---|---|
| [`config/company_domains.yaml`](../config/company_domains.yaml) | `website_domain` per ticker | press (site:), product_docs (required), `refine_for_url` |
| [`config/company_github_orgs.yaml`](../config/company_github_orgs.yaml) | GitHub org slugs per ticker | `github_repos` |
| [`config/company_aliases.yaml`](../config/company_aliases.yaml) | Brand/legal search names | SerpAPI queries (Phase 1 + 2) |

Seed domains/aliases on `ai-collect load-companies`. GitHub orgs are read at
collect time (no DB column).

**Inspector:**

```bash
ai-collect validate-company MSFT
# Shows: website_domain, GitHub orgs, aliases, per-source collector_status
```

---

## Default collection (all 9 sources)

```bash
ai-collect load-companies --validation-set   # or --all for full S&P
ai-collect collect --ticker MSFT             # all enabled collectors
ai-collect collect --source sec github press product_docs --ticker MSFT
ai-collect status
ai-collect validate                          # 0 violations; outcome gate
ai-score score --ticker MSFT --persist
```

Inspect registry:

```bash
ai-collect show-platforms
ai-collect show-platforms --all
```

---

## Collection outcome semantics (Block F)

> **Absence of evidence is not evidence of absence.** Only `reason:source_empty`
> is a weak “no signal in this channel.” Failures and `filtered_to_zero` must not
> be scored as zero AI activity.

Full vocabulary, status table, and validation gate:
[`data-sources.md` § Collection outcome semantics](data-sources.md#collection-outcome-semantics).

Phase 2 collectors follow the same rules:

| Situation | Typical outcome |
|---|---|
| No GitHub orgs configured | `reason:source_empty` |
| GitHub/search returned rows but AI filter removed all | `reason:filtered_to_zero` |
| Product docs: results not on company domain | `reason:filtered_to_zero` |
| Product docs: fetch failed for all URLs | `source_unavailable` (pillar excluded) |
| Missing `SERPAPI_API_KEY` for press/product_docs | `api_key_missing` (pillar excluded) |

---

## File map

```text
src/evidence_collection/
  collectors/github_repos.py
  collectors/press_releases.py
  collectors/product_docs.py
  universe/lookup.py
  universe/github_orgs.py
  registry_gate.py              # enabled platforms (any phase)
src/inference/
  company.py
  scoring.py                    # FORMULA_VERSION = ai_adoption_score_v0_5
config/
  company_github_orgs.yaml
  platforms.yaml                # phase 2 platforms enabled
tests/unit/
  test_github_repos.py  test_github_orgs.py
  test_press_releases.py
  test_product_docs.py
  test_cli_phase2.py  test_inference_cli_phase2.py
  test_universe_lookup.py
```

---

## Known limitations (Phase 2)

- **GitHub org coverage** — only tickers in `company_github_orgs.yaml`; others get
  `source_empty` on the GitHub pillar (not a collection failure).
- **SerpAPI quota** — press, products, hiring, and product-docs discovery share one key;
  no per-collector cost tracking yet (Phase 3).
- **Product docs fetch** — direct HTTP to discovered URLs; no dedicated crawler or
  robots.txt handling.
- **Press vs web_products** — overlapping SerpAPI web results possible; different
  queries and `source_type` metadata.

---

## Adding another Phase 2-style platform

Follow [§6A.4](data-collection-initial-plan.md#6a4-platform-registry-single-source-of-truth):

```text
1. Edit config/platforms.yaml (enabled: true, phase: 2+)
2. Implement collector adapter under src/evidence_collection/collectors/
3. Register in collectors/__init__.py REGISTRY
4. Emit Block F outcome reasons on no_results
5. Bump scoring formula version + WEIGHTS/CAPS if pillar affects score
6. Tests + sync data-sources.md + change-log.md
```

---

*Phase 3 (scale + premium vendors): [`phase-3-development-plan.md`](phase-3-development-plan.md).*
