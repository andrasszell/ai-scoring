from __future__ import annotations

from .base import Collector
from .earnings import EarningsCallCollector
from .patents import PatentsCollector
from .research import ResearchCollector
from .sec_filings import SecFilingsCollector
from .serpapi import HiringCollector, ProductServiceCollector

# Canonical source keys (used by `--source`) -> collector instance.
# Order defines the default execution order.
REGISTRY: dict[str, Collector] = {
    "sec": SecFilingsCollector(),
    "earnings": EarningsCallCollector(),
    "products": ProductServiceCollector(),
    "hiring": HiringCollector(),
    "patents": PatentsCollector(),
    "research": ResearchCollector(),
}

SOURCE_KEYS = list(REGISTRY.keys())

# Document-backed sources that can be re-extracted offline from stored text.
DOCUMENT_SOURCES: dict[str, str] = {
    "sec": "sec_annual_filing",
    "earnings": "earnings_call_transcript",
}


def get_collectors(sources: list[str] | None = None) -> list[Collector]:
    """Return collector instances for the requested source keys (all if None)."""
    if not sources:
        return list(REGISTRY.values())
    unknown = [s for s in sources if s not in REGISTRY]
    if unknown:
        raise ValueError(f"Unknown source(s): {', '.join(unknown)}. Valid: {', '.join(SOURCE_KEYS)}")
    return [REGISTRY[s] for s in sources]


__all__ = ["Collector", "REGISTRY", "SOURCE_KEYS", "DOCUMENT_SOURCES", "get_collectors"]
