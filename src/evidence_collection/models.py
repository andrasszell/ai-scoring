from __future__ import annotations

from dataclasses import dataclass, field

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
    message: str | None = None

    def __post_init__(self) -> None:
        if self.status not in CollectionStatus.ALL:
            raise ValueError(f"Unknown collection status: {self.status!r}")


@dataclass
class CollectionContext:
    """Shared state passed to every collector during a run."""

    conn: object
    run_id: int
    settings: object
    extra: dict = field(default_factory=dict)
