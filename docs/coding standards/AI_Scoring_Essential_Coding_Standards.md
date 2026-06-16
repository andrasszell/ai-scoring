# AI Scoring Project — Essential Coding Standards

These are the minimum coding standards for the AI Adoption Scoring project. Use them when vibe coding with AI assistants. The goal is to prevent messy AI-generated code, protect scoring integrity, and keep the project reproducible.

---

## 1. Core Rule

Every code change must preserve three things:

1. **Evidence traceability** — every collected signal must be linked to its source.
2. **Scoring explainability** — every score must be explainable from visible inputs and formulas.
3. **Reproducibility** — another developer must be able to run the same pipeline and get the same result, or understand why not.

No feature is accepted if it breaks one of these.

---

## 2. Project Boundaries

The codebase should stay clearly separated into two domains:

### A. Data Collection

Responsible for:

- finding company data sources
- fetching or importing raw evidence
- normalizing source metadata
- storing raw or lightly cleaned evidence
- detecting duplicates
- recording collection timestamps
- recording source reliability

Not responsible for:

- final AI adoption score calculation
- mathematical weighting models
- changing scoring formulas
- interpreting strategic meaning beyond basic extraction

### B. Data Processing and Scoring

Responsible for:

- transforming evidence into structured signals
- assigning confidence
- calculating category scores
- calculating final AI adoption scores
- explaining score drivers
- comparing companies
- uncertainty and sensitivity analysis

Not responsible for:

- scraping logic
- API fetching logic
- raw source discovery
- changing evidence records silently

If a file mixes collection logic and scoring logic, refactor before adding more functionality.

---

## 3. Required Folder Discipline

Use a simple structure like this:

```text
/src
  /collection        # source connectors, fetchers, raw evidence import
  /processing        # cleaning, extraction, signal generation
  /scoring           # formulas, weights, confidence, final score
  /models            # shared data models / schemas
  /storage           # database or file persistence layer
  /cli               # command-line entry points
/tests
  /unit
  /integration
  /fixtures
/docs
  project-control.md
  implementation-plan.md
  data-sources.md
  scoring-methodology.md
  change-log.md
```

Do not create new top-level folders unless there is a clear long-term reason.

---

## 4. Data Model Standards

Every evidence item must have at least:

```text
company_id
source_url or source_id
source_type
retrieved_at
evidence_text or evidence_payload
collector_name or connector_name
confidence_initial
raw_hash
```

Every derived signal must have at least:

```text
company_id
evidence_id
signal_type
signal_value
confidence
extraction_method
created_at
explanation
```

Every score must have at least:

```text
company_id
score_type
score_value
score_version
input_signal_ids
formula_version
created_at
explanation
```

Never calculate a score from untraceable data.

---

## 5. Scoring Code Standards

Scoring code must be boring, explicit, and testable.

Rules:

- Put formulas in `/src/scoring`, not inside notebooks, scrapers, or CLI scripts.
- Every formula must have a named version, for example `ai_adoption_score_v0_1`.
- No hidden weights. All weights must live in a visible config file or named constants.
- No magic numbers inside scoring functions.
- Every scoring function must return both the numeric score and an explanation object.
- If confidence affects the score, confidence logic must be separate from the raw score formula.
- Never overwrite old score versions without keeping the version history.

Preferred scoring function shape:

```python
def calculate_company_score(signals: list[Signal], config: ScoringConfig) -> ScoreResult:
    """Return score, confidence, explanation, and input signal references."""
```

---

## 6. Evidence and Source Standards

Source quality matters as much as quantity.

Each source should be classified as one of:

```text
official_company
regulatory_filing
job_posting
press_release
technical_blog
product_documentation
news_article
third_party_database
social_media
unknown
```

Each source should receive a reliability level:

```text
high
medium
low
unknown
```

Rules:

- Official company sources are not automatically true; they are claims with source context.
- News articles are secondary evidence unless they contain direct company statements.
- Job postings are strong evidence for capability demand, not proof of deployed AI systems.
- Vendor case studies are useful but must be marked as potentially promotional.
- One weak source should not dominate a company score.

---

## 7. Testing Minimums

Every meaningful change needs tests.

Required tests by area:

### Data Collection

Test:

- URL/source parsing
- duplicate detection
- source metadata creation
- failure handling
- raw evidence hashing

### Processing

Test:

- extraction from fixture evidence
- handling missing fields
- confidence assignment
- malformed input behavior

### Scoring

Test:

- exact formula output on small known examples
- weight changes affect output as expected
- missing signals reduce confidence but do not crash
- score explanations include input signal IDs
- score version is recorded

### Regression

Add a regression test whenever:

- a wrong score was produced
- evidence was lost
- a source was misclassified
- AI-generated code introduced a bug
- a formula changed unintentionally

Minimum command before accepting a change:

```bash
pytest
```

For scoring changes, also run a small deterministic fixture test.

---

## 8. Fixture Standards

Use small, realistic fixtures.

Fixtures should include:

```text
company profile
raw evidence examples
expected extracted signals
expected score outputs
```

Keep at least one tiny end-to-end fixture:

```text
raw evidence -> processed signals -> score -> explanation
```

This fixture protects the whole project from AI-generated drift.

---

## 9. AI Coding Workflow

For every AI coding task, give the assistant this structure:

```text
Objective:
Files allowed to change:
Files not allowed to change:
Expected behavior:
Non-goals:
Test requirements:
Definition of done:
```

Never ask the AI to “improve the project” without boundaries.

Use this default instruction:

```text
Implement only the requested step. Do not refactor unrelated files. Do not add dependencies. Preserve evidence traceability, scoring explainability, and reproducibility. Add or update tests for changed behavior. Stop and explain if the requested change requires modifying unapproved files or changing the scoring methodology.
```

---

## 10. Dependency Rule

Do not add a new dependency unless it clearly solves a real project need.

Before adding a dependency, record:

```text
package name
reason
alternative considered
risk level
setup impact
tests affected
```

Default preference:

1. Python standard library
2. existing project dependency
3. small well-maintained library
4. large framework only with explicit approval

Never add a dependency just because generated code suggested it.

---

## 11. Debugging Rule

When something fails, diagnose before fixing.

Required debug note:

```text
Symptom:
Failing command:
Expected behavior:
Actual behavior:
Most likely layer:
Evidence:
Minimal fix plan:
Files allowed to change:
```

Do not allow AI to randomly patch multiple files.

Do not weaken tests to make them pass.

---

## 12. Code Review Minimum

Before accepting AI-generated code, check:

```text
What changed?
Why did it change?
Which requirement does it satisfy?
Which files changed?
Were any surprise files changed?
How was it tested?
Did scoring behavior change?
Did evidence traceability remain intact?
Did any dependency change?
What risk remains?
```

Reject the change if:

- scoring formulas changed without approval
- source/evidence links were removed
- tests were weakened
- unrelated files changed
- a new dependency appeared without explanation
- raw data is overwritten silently
- explanations are missing from score outputs

---

## 13. Documentation Minimum

Keep only these essential docs current:

```text
/docs/project-control.md        # current scope, non-goals, architecture
/docs/implementation-plan.md    # current task plan
/docs/data-sources.md           # approved data sources and source quality rules
/docs/scoring-methodology.md    # formulas, weights, confidence rules, score versions
/docs/change-log.md             # important changes and decisions
/docs/setup.md                  # how to run the project
```

**Supplementary** (phase guides and strategy — keep in sync when phases change):

```text
/docs/README.md                      # doc map (entry point)
/docs/phase-1-development-plan.md    # Phase 1 checklist (complete)
/docs/phase-2-implementation.md    # Phase 2 reference (complete)
/docs/phase-3-development-plan.md    # Phase 3 checklist (planned)
/docs/data-collection-initial-plan.md  # Team 1 strategy; §6A registry
```

When scoring logic changes, update `scoring-methodology.md` in the same change.

When data source rules change, update `data-sources.md` in the same change.

---

## 14. Definition of Done

A task is done only when:

```text
[ ] The change matches the requested scope.
[ ] No unrelated files changed.
[ ] Evidence remains traceable to source.
[ ] Scores remain explainable.
[ ] Formula/config versions are preserved.
[ ] Tests were added or updated.
[ ] pytest passes, or failures are documented.
[ ] No new dependency was added without approval.
[ ] Relevant docs were updated.
[ ] Remaining risks are stated.
```

---

## 15. Absolute Non-Negotiables

Never accept code that:

- calculates a company score without source-linked evidence
- hides scoring weights inside implementation details
- changes scoring formulas without versioning
- mixes scraping/fetching with scoring formulas
- silently drops evidence
- silently overwrites scores
- treats AI-generated extraction as ground truth without confidence
- removes tests because they are inconvenient
- adds broad abstractions before the pipeline is stable
- makes results impossible to reproduce
