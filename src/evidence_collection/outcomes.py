from __future__ import annotations

import re

REASON_PREFIX = "reason:"


class OutcomeReason:
    """Controlled vocabulary for collection outcome sub-reasons (Block F)."""

    SOURCE_EMPTY = "source_empty"
    FILTERED_TO_ZERO = "filtered_to_zero"
    PARTIAL_SUCCESS = "partial_success"

    ALL = frozenset({SOURCE_EMPTY, FILTERED_TO_ZERO, PARTIAL_SUCCESS})


_REASON_RE = re.compile(rf"^{REASON_PREFIX}([a-z_]+)(?:\s*[—–-]\s*(.*))?$")


def format_outcome_message(reason: str, detail: str | None = None) -> str:
    """Build collector_status.message with a machine-readable reason prefix."""
    if reason not in OutcomeReason.ALL:
        raise ValueError(f"Unknown outcome reason: {reason!r}")
    text = f"{REASON_PREFIX}{reason}"
    if detail and str(detail).strip():
        text = f"{text} — {str(detail).strip()}"
    return text


def parse_outcome_reason(message: str | None) -> str | None:
    """Extract outcome reason code from collector_status.message, if present."""
    if not message:
        return None
    match = _REASON_RE.match(message.strip())
    if not match:
        return None
    code = match.group(1)
    return code if code in OutcomeReason.ALL else None


def parse_outcome_detail(message: str | None) -> str | None:
    """Human detail after the reason prefix, if any."""
    if not message:
        return None
    match = _REASON_RE.match(message.strip())
    if not match:
        return message
    return match.group(2) or None
