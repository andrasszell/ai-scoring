from __future__ import annotations

from .models import CollectorResult
from .platforms import Platform, Registry, auth_status, load_registry
from .status import CollectionStatus

_REGISTRY: Registry | None = None


def reset_registry_cache() -> None:
    """Clear cached platform registry (for tests)."""
    global _REGISTRY
    _REGISTRY = None
    from .sources import reset_profile_cache

    reset_profile_cache()


def get_platform_registry() -> Registry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = load_registry()
    return _REGISTRY


def enabled_cli_sources(*, phase: int = 1) -> frozenset[str]:
    registry = get_platform_registry()
    return frozenset(p.cli_source for p in registry.platforms_enabled(phase=phase))


def platform_for_collector(collector) -> Platform | None:
    """Resolve registry platform by collector.platform_id, then collector name."""
    registry = get_platform_registry()
    platform_id = getattr(collector, "platform_id", None)
    if platform_id:
        platform = registry.platform_by_id(platform_id)
        if platform is not None:
            return platform
    name = collector.name if hasattr(collector, "name") else str(collector)
    return registry.platform_by_collector(name)


def platform_for_collector_name(collector_name: str) -> Platform | None:
    return get_platform_registry().platform_by_collector(collector_name)


def api_key_missing_result(collector) -> CollectorResult:
    platform = platform_for_collector(collector)
    name = collector.name if hasattr(collector, "name") else str(collector)
    if platform and platform.auth.env_key:
        return CollectorResult(
            CollectionStatus.API_KEY_MISSING,
            message=f"missing_{platform.auth.env_key.lower()}",
        )
    return CollectorResult(
        CollectionStatus.API_KEY_MISSING,
        message=f"missing_api_key:{name}",
    )


def collector_gate(collector) -> CollectorResult | None:
    """Return a short-circuit result when registry blocks collection, else None."""
    platform = platform_for_collector(collector)
    if platform is None:
        return None
    if not platform.enabled or platform.phase != 1:
        return CollectorResult(
            CollectionStatus.SKIPPED,
            message=f"platform_disabled:{platform.id}",
        )
    if platform.auth.env_key and platform.auth.required and auth_status(platform.auth) == "missing":
        return api_key_missing_result(collector)
    return None
