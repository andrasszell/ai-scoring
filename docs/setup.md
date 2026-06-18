# Setup

How to run the project (Coding Standards §13). See [`../README.md`](../README.md) for CLI overview.
**Doc index:** [`README.md`](README.md) · [`project-control.md`](project-control.md).

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # then edit
```

Set at least the SEC contact (required by EDGAR fair-access):

```bash
SEC_USER_AGENT="Your Name your.email@example.com"
```

Optional API keys — see [`data-sources.md`](data-sources.md) for all platforms:
`FMP_API_KEY`, `SERPAPI_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY`, `PATENTSVIEW_API_KEY`,
`GITHUB_TOKEN` (optional; higher GitHub rate limits).
Collectors without their key are skipped and record an `api_key_missing` status.

## Smallest end-to-end run (no paid keys)

```bash
ai-collect init-db
ai-collect collect --ticker MSFT NVDA --source sec   # SEC needs no API key
ai-collect status
ai-collect export-all --output-dir data/exports
ai-score score --ticker MSFT NVDA                    # inference layer
```

## Tests

```bash
pytest                       # all
pytest tests/unit            # fast unit tests
pytest tests/integration     # end-to-end fixture + run orchestration
```

## Phase 3 full S&P 500 collect (3A.7)

One-shot production run (several hours, paid API usage):

```bash
bash scripts/phase3_sp500_run.sh
```

QA checklist and monitoring: [`qa/phase-3-sp500-run.md`](qa/phase-3-sp500-run.md).

## Environment overrides (defaults shown)

```bash
AI_DEPTH_DB="data/evidence.sqlite"
AI_DEPTH_RAW_DIR="data/raw"
AI_DEPTH_EXPORT_DIR="data/exports"
REQUEST_TIMEOUT="30"
MAX_CANDIDATE_PARAGRAPHS="40"
```
