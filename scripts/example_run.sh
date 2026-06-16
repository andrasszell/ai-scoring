#!/usr/bin/env bash
set -euo pipefail

# Evidence Discovery Layer demo: collect, export, then score (separate layer).

ai-collect init-db
# Load the full universe (one cheap request) so the default companies exist.
ai-collect load-companies
# No --ticker/--all: collects the default top S&P 500 companies.
# --source limits to keys that need no paid API access.
ai-collect collect --source sec research

# Inspect what happened (status per company/source).
ai-collect status

# Clean exports for the inference team.
ai-collect export-all --output-dir data/exports

# Inference layer (separate tool) reads the corpus and produces scores.
ai-score export-scores --output data/exports/ai_depth_scores.csv
