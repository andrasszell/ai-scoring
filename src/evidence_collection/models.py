from __future__ import annotations

from dataclasses import dataclass, field

from .outcomes import OutcomeReason, format_outcome_message
from .status import CollectionStatus


@dataclass
class CollectorResult:
    """Outcome of running one collector against one company.

    Carries the structured status plus operational counts. Collectors return this
    instead of raising, so a single source failure never aborts a run and the
    status is always recorded.
    """

    status: str
    evidence_count: int = 0
    documents_count: int = 0
    api_calls: int = 0
    source_hits: int = 0
    candidates_after_filter: int = 0
    message: str | None = None
    outcome_reason: str | None = None

    def __post_init__(self) -> None:
        if self.status not in CollectionStatus.ALL:
            raise ValueError(f"Unknown collection status: {self.status!r}")
        if self.outcome_reason and self.outcome_reason not in OutcomeReason.ALL:
            raise ValueError(f"Unknown outcome reason: {self.outcome_reason!r}")
        if self.outcome_reason and self.status not in (
            CollectionStatus.SUCCESS,
            CollectionStatus.NO_RESULTS,
        ):
            raise ValueError(
                f"outcome_reason only applies to success/no_results, not {self.status!r}"
            )

    def storage_message(self) -> str | None:
        """Message persisted to collector_status (includes reason: prefix when set)."""
        if self.outcome_reason:
            return format_outcome_message(self.outcome_reason, self.message)
        return self.message


def collector_result(
    status: str,
    *,
    outcome_reason: str | None = None,
    message: str | None = None,
    evidence_count: int = 0,
    documents_count: int = 0,
    api_calls: int = 0,
    source_hits: int = 0,
    candidates_after_filter: int = 0,
) -> CollectorResult:
    """Build a CollectorResult; sets outcome_reason on success/no_results runs."""
    return CollectorResult(
        status=status,
        evidence_count=evidence_count,
        documents_count=documents_count,
        api_calls=api_calls,
        source_hits=source_hits,
        candidates_after_filter=candidates_after_filter,
        message=message,
        outcome_reason=outcome_reason,
    )


@dataclass
class CollectionContext:
    """Shared state passed to every collector during a run."""

    conn: object
    run_id: int
    settings: object
    extra: dict = field(default_factory=dict)
