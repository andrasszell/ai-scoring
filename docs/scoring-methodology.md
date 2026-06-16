# AI Depth Score — Methodology (MVP)

*A plain-language guide for finance colleagues to how we measure how deeply S&P 500 companies use AI.*

> **Status: MVP / proof of concept.** The pipeline end-to-end works and produces
> scores today, but the scoring is a deliberately simple first version. Please
> read the **"What this is NOT yet"** and **"Known limitations"** sections before
> using any score in analysis. Treat current numbers as a plumbing demo, not an
> investment signal.

> **Architecture note (June 2026).** The platform is now split into two layers
> with a strict separation of duties:
>
> - **Evidence Discovery Layer** (`ai-collect`) finds and preserves evidence. It
>   does *not* score companies. See `docs/Implementation Plan for Data Collection Team.md`.
> - **Inference Layer** (`ai-score`) reads the evidence corpus and produces the AI
>   Depth Score described below.
>
> This document describes the *inference* layer's MVP score. The pillars below are
> now derived from the collected evidence corpus (the `evidence_items` table),
> grouped by the collector that produced each item.

---

## 1. What we are trying to measure

We want a repeatable, evidence-backed indicator of **how deeply a company actually
uses AI** — not just whether it talks about AI. Marketing mentions are cheap; we
care about AI showing up in products, hiring, R&D, and official disclosures.

The output is an **AI Depth Score from 0 to 100** per company, broken down into
the contributing components, plus the **underlying evidence** behind every number
so any score can be audited back to a primary source.

---

## 2. The six evidence pillars

We gather evidence across six independent "pillars," each from a different source.
The idea is that a company genuinely deep in AI should show up in several of them,
not just one.

| # | Pillar | What it captures | Source | Data quality |
|---|---|---|---|---|
| 1 | **Annual report (10-K)** | AI language in official SEC filings | SEC EDGAR | High (audited disclosures) |
| 2 | **Earnings calls** | What management says about AI to investors | Financial Modeling Prep | High (verbatim transcripts) |
| 3 | **Products / services** | AI in the company's actual offerings | Google search (SerpAPI) | Medium (web signal) |
| 4 | **Hiring intensity** | Demand for AI/ML talent (job postings, incl. LinkedIn) | Google Jobs via SerpAPI | Medium (real postings) |
| 5 | **Patents** | AI-related inventions | PatentsView | Medium (name-matching) |
| 6 | **Research papers** | AI scientific output | Semantic Scholar | Medium (name-matching) |

---

## 3. How the data flows

The process is split into three deliberately separate stages. This separation is
important: it means we can re-run scoring or audit evidence **without re-collecting
data**, and we always keep the raw source material.

```
   COLLECT                  STORE                    SCORE
 (gather evidence)   →   (central database)   →   (compute 0–100)

  SEC filings        ┐
  Earnings calls     ┤
  Products (web)     ┼─► SQLite database ─► weighted score per company
  Hiring (jobs/LinkedIn) ┤  - companies        + per-pillar breakdown
  Patents            ┤    - source documents   + full evidence trail
  Research           ┘    - evidence paragraphs
                          - metrics (counts)
```

### Stage 1 — Collect

For each company, each pillar runs independently. The collector:

1. Fetches the source (e.g. downloads the latest 10-K from SEC).
2. Extracts the relevant passages — for text sources we keep **paragraphs that
   mention AI terms** (artificial intelligence, machine learning, LLMs, neural
   networks, computer vision, etc.).
3. Saves each passage as an **evidence record** linked to its source document.
4. Records a **count metric** (e.g. "18 AI paragraphs in the 10-K").

If a source is unavailable or a required API key is missing, that pillar is
**skipped and logged** — it does not crash the run or silently inflate the score.

### Stage 2 — Store

Everything lands in a local database. The key tables are:

- **companies** — the universe (ticker, name, sector, SEC identifier, aliases).
- **documents** — each source filing/transcript (the audit anchor), with a content
  hash and stored raw + extracted text for reproducibility.
- **evidence_items** — every candidate AI passage we found, linked back to its
  document, tagged with the collector name + version that produced it.
- **collector_status** — for every company/source, whether collection succeeded,
  found nothing, or failed (and why). *Absence of evidence is not evidence of absence.*

Because evidence links to documents, **every score is traceable to a primary
source** (e.g. an exact paragraph in a named 10-K with the SEC URL and filing date).

> Counts used for scoring are derived by the inference layer from `evidence_items`
> (grouped by collector); the collection layer no longer stores any AI-maturity
> numbers — only operational metrics like runtime and item counts.

### Stage 3 — Score

We convert the raw counts into the 0–100 score (details below).

---

## 4. How the score is calculated — in detail

The score combines the six pillars using **weights** (how much each pillar matters)
and **caps** (the count at which a pillar is considered "maxed out").

### Step-by-step

For each pillar:

1. Take the raw count (e.g. 18 AI paragraphs in the 10-K).
2. **Cap and normalise** it to a 0–1 ratio: `min(count / cap, 1.0)`.
   - The cap prevents a single very "chatty" source from dominating. Once a
     company hits the cap, more mentions don't add points.
3. Multiply by the pillar's weight (points).

Then **sum all six** pillar contributions → the AI Depth Score (max 100).

### Current weights and caps

| Pillar | Weight (max points) | Cap (count = full marks) |
|---|---:|---:|
| Annual report (10-K) | 25 | 20 paragraphs |
| Earnings calls | 20 | 12 paragraphs |
| Products / services | 25 | 8 results |
| Hiring intensity | 15 | 8 results |
| Patents | 10 | 10 patents |
| Research papers | 5 | 5 papers |
| **Total** | **100** | |

### Worked example — Microsoft (data as of June 2026)

| Pillar | Raw count | Cap | Ratio | × Weight | Points |
|---|---:|---:|---:|---:|---:|
| Annual report (10-K) | 15 | 20 | 0.75 | × 25 | **18.75** |
| Products / services | 8 | 8 | 1.00 (capped) | × 25 | **25.0** |
| Hiring intensity (incl. 6 LinkedIn) | 10 | 8 | 1.00 (capped) | × 15 | **15.0** |
| Research papers | 10 | 5 | 1.00 (capped) | × 5 | **5.0** |
| Earnings / Patents | 0 | — | 0 | — | 0.0 |
| **AI Depth Score** | | | | | **63.75** |

Earnings and patents are 0 here only because we have not yet supplied those API
keys (see limitations). Adding them would raise the score further. (Numbers will
change as filings and data sources update — they illustrate the mechanism, not a
fixed result.)

---

## 5. What you get as output

The collection layer exports the evidence corpus (`ai-collect export-all`):
`companies.csv`, `documents.csv`, `evidence_items.csv`, `collector_status.csv`,
and `evidence_items.jsonl`. The inference layer adds:

- **`ai_depth_scores.csv`** (`ai-score export-scores`) — one row per investigated
  company: the total score and each collector's point contribution. *Only companies
  with collected evidence are listed; running the full universe lists all of them.*
- **`evidence_items.csv`** — the underlying evidence: every AI passage, its source,
  the collector that found it, and a link to the source document.

This means a finance reviewer can start from a score, drill into the exact
paragraphs that produced it, and verify them against the original filing.

---

## 6. What this is NOT yet (important)

To set expectations clearly:

- **It is not a quality judgement.** We currently count *how much* AI is mentioned
  / found, not *how good or material* it is. A company that mentions AI 20 times
  is not necessarily "deeper" than one that mentions it 8 times.
- **It is not sector-adjusted.** A bank and a chipmaker are scored on the same
  scale, even though "deep AI use" looks very different in each.
- **It is not de-duplicated across corporate structure.** Patents/research are
  matched on company name, so subsidiaries and name variants are imperfectly
  captured.
- **The weights and caps are placeholders.** They were chosen by judgement, not
  calibrated against any ground-truth outcome.

---

## 7. Known limitations at this stage

| Area | Limitation | Impact |
|---|---|---|
| **Coverage** | 10-K, products, and hiring are active; earnings, patents, and (reliable) research still need API keys not yet provisioned | Those pillars currently read 0, understating scores |
| **Brand vs legal name** | Web/job sources index employers by brand, not legal name (e.g. Alphabet→Google); handled via a small alias map | Some companies miss a pillar (e.g. Google's own postings don't appear in Google Jobs) |
| **Hiring signal** | Uses Google Jobs postings (incl. LinkedIn) but counts are page-limited and not deduplicated | Reasonable proxy; not a true headcount/role-share measure |
| **Patents/research matching** | Name-based, no subsidiary/legal-entity mapping | Both false positives and misses |
| **Measurement** | Whole-word keyword counting, not meaning | Avoids obvious false matches, but still can't tell substantive AI use from boilerplate/risk-factor mentions |
| **Normalisation** | Raw scores, no sector or size adjustment | Cross-company comparisons are rough |
| **Calibration** | Weights/caps not validated against outcomes | Score levels are indicative only |
| **Transcript availability** | Earnings transcripts typically require a paid data plan | Pillar 2 may stay empty without licensing |

---

## 8. Where this goes next (proposed roadmap)

In rough priority order:

1. **Provision data access** — add the API keys so all six pillars populate
   (biggest immediate improvement to coverage).
2. **Move from counting to understanding** — use an LLM to classify the retrieved
   passages (e.g. "core product" vs "risk disclosure" vs "buzzword"), so we score
   substance, not volume.
3. **Sector-adjusted percentiles** — rank companies within their sector so scores
   are comparable across very different business models.
4. **Better hiring and entity data** — replace web-search proxies with a real
   job-postings provider and proper subsidiary/legal-name mapping for patents.
5. **Per-company evidence cards** — a one-page, citation-backed summary per
   company for analyst review.

---

## 9. Quick FAQ

**Can I trust a specific score today?**
Use it as a directional, demo-stage indicator and always check the underlying
evidence. Do not use it as a standalone signal yet.

**Why do some big tech names score lower than expected?**
Most likely because pillars beyond the 10-K aren't collected yet (no API keys), or
because their AI work shows up in products/patents we haven't enabled — not because
they don't use AI.

**Can we add companies outside the default list?**
Yes — any S&P 500 company can be collected on request, or the entire index at once.
We can also analyze **any SEC-listed company** by name (even non-index ones, e.g.
Elanco Animal Health); the tool falls back to the full SEC filer directory.

**How auditable is it?**
Fully. Every score decomposes into pillar points, and every pillar decomposes into
specific evidence passages tied to named source documents.

---

*This document describes the MVP as currently implemented. Methodology, weights,
and data sources are expected to change as the project matures.*
