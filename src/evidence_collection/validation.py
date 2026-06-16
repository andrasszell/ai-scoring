from __future__ import annotations

# Data validation for evidence (Coding Standards §14, §22 non-negotiables).
# The hard rule we enforce at insert time: never store evidence without a source
# URL or a source date, and never without the fields that make it traceable.

REQUIRED_NONEMPTY = ("ticker", "evidence_text", "collector_name", "collector_version")


def _empty(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    return False


def validate_evidence(row: dict) -> list[str]:
    """Return a list of validation errors for an evidence row (empty = valid)."""
    errors = [f"missing {f}" for f in REQUIRED_NONEMPTY if _empty(row.get(f))]
    # §22: evidence must be anchored to a source URL or a source date.
    if _empty(row.get("source_url")) and _empty(row.get("source_date")):
        errors.append("missing both source_url and source_date")
    return errors


def is_valid_evidence(row: dict) -> bool:
    return not validate_evidence(row)
