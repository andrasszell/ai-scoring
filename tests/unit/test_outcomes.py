import pytest

from evidence_collection.outcomes import (
    OutcomeReason,
    format_outcome_message,
    parse_outcome_detail,
    parse_outcome_reason,
)


def test_format_outcome_message_with_detail():
    msg = format_outcome_message(OutcomeReason.SOURCE_EMPTY, "no listings")
    assert msg == "reason:source_empty — no listings"


def test_format_outcome_message_rejects_unknown():
    with pytest.raises(ValueError):
        format_outcome_message("not_a_reason")


def test_parse_outcome_reason_and_detail():
    msg = "reason:filtered_to_zero — filing stored; no AI paragraphs"
    assert parse_outcome_reason(msg) == OutcomeReason.FILTERED_TO_ZERO
    assert parse_outcome_detail(msg) == "filing stored; no AI paragraphs"


def test_parse_outcome_reason_returns_none_for_legacy_message():
    assert parse_outcome_reason("no_transcripts") is None
    assert parse_outcome_detail("no_transcripts") == "no_transcripts"
