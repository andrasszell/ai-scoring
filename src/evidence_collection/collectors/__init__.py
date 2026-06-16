from __future__ import annotations

from .base import Collector
from .earnings import EarningsCallCollector
from .patents import PatentsCollector
from .research import ResearchCollector
from .sec_filings import SecFilingsCollector
from .serpapi import HiringCollector, ProductServiceCollector
from ..registry_gate import (
    api_key_missing_result,
    collector_gate,
    enabled_cli_sources,
    get_platform_registry,
    platform_for_collector,
    reset_registry_cache,
)

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

COLLECTOR_BY_NAME: dict[str, Collector] = {c.name: c for c in REGISTRY.values()}

# Document-backed sources that can be re-extracted offline from stored text.
DOCUMENT_SOURCES: dict[str, str] = {
    "sec": "sec_annual_filing",
    "earnings": "earnings_call_transcript",
}


def get_collectors(sources: list[str] | None = None) -> list[Collector]:
    """Return collector instances for the requested source keys.

    When ``sources`` is omitted, only phase-1 enabled platforms from the registry
    are included. Explicit ``--source`` requests still return the collector so the
    runner can record ``skipped`` or ``api_key_missing`` from registry rules.
    """
    if sources:
        unknown = [s for s in sources if s not in REGISTRY]
        if unknown:
            raise ValueError(f"Unknown source(s): {', '.join(unknown)}. Valid: {', '.join(SOURCE_KEYS)}")
        return [REGISTRY[s] for s in sources]
    enabled = enabled_cli_sources()
    return [REGISTRY[key] for key in SOURCE_KEYS if key in enabled]


__all__ = [
    "COLLECTOR_BY_NAME",
    "Collector",
    "DOCUMENT_SOURCES",
    "REGISTRY",
    "SOURCE_KEYS",
    "api_key_missing_result",
    "collector_gate",
    "enabled_cli_sources",
    "get_collectors",
    "get_platform_registry",
    "platform_for_collector",
    "reset_registry_cache",
]
