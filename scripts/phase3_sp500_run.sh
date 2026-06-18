#!/usr/bin/env bash
# Phase 3A.7 — full S&P 500 production collect (see docs/qa/phase-3-sp500-run.md).
#
# Usage:
#   bash scripts/phase3_sp500_run.sh              # full pipeline
#   PHASE=collect bash scripts/phase3_sp500_run.sh  # collect only
#   PHASE=post bash scripts/phase3_sp500_run.sh     # validate/export after collect
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

DATE_TAG="${DATE_TAG:-$(date +%Y%m%d)}"
EXPORT_DIR="data/exports/phase3_sp500_${DATE_TAG}"
PHASE="${PHASE:-all}"
mkdir -p "$EXPORT_DIR"

echo "Phase 3A.7 — phase=${PHASE}, export: ${EXPORT_DIR}"

_run_collect() {
  ai-collect load-companies 2>&1 | tee "${EXPORT_DIR}/load-companies.log"
  ai-collect verify-universe 2>&1 | tee "${EXPORT_DIR}/verify-universe.log"
  echo "Starting collect --all (509 companies × 9 collectors; expect several hours)..."
  ai-collect collect --all 2>&1 | tee "${EXPORT_DIR}/collect.log"
}

_run_post() {
  ai-collect validate 2>&1 | tee "${EXPORT_DIR}/validate.log"
  ai-collect costs --project-full-sp500 2>&1 | tee "${EXPORT_DIR}/costs.log"
  ai-collect freshness --stale-only 2>&1 | tee "${EXPORT_DIR}/freshness.log"
  if [[ "${SKIP_RETRY:-0}" != "1" ]]; then
    echo "Retrying transient failures (set SKIP_RETRY=1 to skip)..."
    ai-collect retry-failed 2>&1 | tee "${EXPORT_DIR}/retry-failed.log" || true
  fi
  ai-collect export-all --output-dir "${EXPORT_DIR}" 2>&1 | tee "${EXPORT_DIR}/export.log"
  echo "Done. Archive: ${EXPORT_DIR}"
}

case "$PHASE" in
  all)
    _run_collect
    _run_post
    ;;
  collect)
    _run_collect
    echo "Collect finished. Run: PHASE=post DATE_TAG=${DATE_TAG} bash scripts/phase3_sp500_run.sh"
    ;;
  post)
    _run_post
    ;;
  *)
    echo "Unknown PHASE=${PHASE} (use all, collect, or post)" >&2
    exit 1
    ;;
esac
