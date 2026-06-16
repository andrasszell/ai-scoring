# Setup

How to run the project (Coding Standards §13). See `../README.md` for full CLI usage.

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

Optional API keys (collectors without their key are skipped and record an
`api_key_missing` status): `FMP_API_KEY`, `SERPAPI_API_KEY`,
`SEMANTIC_SCHOLAR_API_KEY`, `PATENTSVIEW_API_KEY`.

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

## Environment overrides (defaults shown)

```bash
AI_DEPTH_DB="data/evidence.sqlite"
AI_DEPTH_RAW_DIR="data/raw"
AI_DEPTH_EXPORT_DIR="data/exports"
REQUEST_TIMEOUT="30"
MAX_CANDIDATE_PARAGRAPHS="40"
```
