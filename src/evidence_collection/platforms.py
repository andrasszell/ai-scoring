from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

from .config import settings
from .sources import Reliability, SourceCategory

AuthStatus = Literal["ok", "missing", "not_required"]

# Collectors implemented in Phase 1 (must exist when phase==1 and enabled==true).
KNOWN_COLLECTOR_NAMES = frozenset(
    {"sec_filings", "earnings_calls", "web_products", "hiring_jobs", "patents", "research"}
)

_ALLOWED_CATEGORIES = frozenset(
    {
        SourceCategory.OFFICIAL_COMPANY,
        SourceCategory.REGULATORY_FILING,
        SourceCategory.JOB_POSTING,
        SourceCategory.PRESS_RELEASE,
        SourceCategory.TECHNICAL_BLOG,
        SourceCategory.PRODUCT_DOCUMENTATION,
        SourceCategory.NEWS_ARTICLE,
        SourceCategory.THIRD_PARTY_DATABASE,
        SourceCategory.SOCIAL_MEDIA,
        SourceCategory.UNKNOWN,
    }
)
_ALLOWED_RELIABILITY = frozenset(
    {Reliability.HIGH, Reliability.MEDIUM, Reliability.LOW, Reliability.UNKNOWN}
)


@dataclass(frozen=True)
class AuthConfig:
    env_key: str
    required: bool
    notes: str | None = None


@dataclass(frozen=True)
class Loader:
    id: str
    display_name: str
    vendor: str
    api_base_url: str
    auth: AuthConfig
    phase: int
    enabled: bool
    cost_model: str
    rate_limit_notes: str | None = None
    cli_command: str | None = None
    notes: str | None = None


@dataclass(frozen=True)
class Platform:
    id: str
    collector: str
    cli_source: str
    source_type: str
    display_name: str
    vendor: str
    api_base_url: str
    auth: AuthConfig
    phase: int
    enabled: bool
    cost_model: str
    source_category: str
    source_reliability: str
    confidence_initial: float
    rate_limit_notes: str | None = None
    reprocessable: bool = False
    collector_version: str | None = None
    notes: str | None = None


@dataclass(frozen=True)
class Registry:
    registry_version: str
    loaders: tuple[Loader, ...]
    platforms: tuple[Platform, ...]

    def loaders_enabled(self, *, phase: int | None = None) -> list[Loader]:
        rows = [l for l in self.loaders if l.enabled]
        if phase is not None:
            rows = [l for l in rows if l.phase == phase]
        return rows

    def platforms_enabled(self, *, phase: int | None = 1) -> list[Platform]:
        rows = [p for p in self.platforms if p.enabled]
        if phase is not None:
            rows = [p for p in rows if p.phase == phase]
        return rows

    def platform_by_collector(self, name: str) -> Platform | None:
        for p in self.platforms:
            if p.collector == name:
                return p
        return None

    def platform_by_id(self, platform_id: str) -> Platform | None:
        for p in self.platforms:
            if p.id == platform_id:
                return p
        return None

    def platform_by_cli_source(self, cli_source: str) -> Platform | None:
        for p in self.platforms:
            if p.cli_source == cli_source:
                return p
        return None

    def auth_status(self, entry: Platform | Loader) -> AuthStatus:
        """Return auth readiness for a platform or loader (reads env via os.getenv)."""
        return auth_status(entry.auth)


def default_registry_path() -> Path:
    if settings.platforms_yaml:
        return settings.platforms_yaml
    env_path = os.getenv("PLATFORMS_YAML")
    if env_path:
        return Path(env_path)
    # Package lives at src/evidence_collection/; project root is two levels up.
    project_root = Path(__file__).resolve().parents[2]
    candidate = project_root / "config" / "platforms.yaml"
    if candidate.is_file():
        return candidate
    return Path.cwd() / "config" / "platforms.yaml"


def load_registry(path: Path | None = None) -> Registry:
    """Load and validate config/platforms.yaml (Coding Standards §6A.4)."""
    registry_path = path or default_registry_path()
    if not registry_path.is_file():
        raise FileNotFoundError(f"Platform registry not found: {registry_path}")
    raw = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Platform registry must be a mapping: {registry_path}")
    version = _require_str(raw, "registry_version", context="registry")
    loaders = _parse_loaders(raw.get("loaders") or [], registry_path)
    platforms = _parse_platforms(raw.get("platforms") or [], registry_path)
    return Registry(registry_version=version, loaders=tuple(loaders), platforms=tuple(platforms))


def auth_status(auth: AuthConfig) -> AuthStatus:
    """Check whether the configured env var is present for a loader or platform."""
    if not auth.required or not auth.env_key:
        return "not_required"
    value = os.getenv(auth.env_key, "").strip()
    if not value:
        return "missing"
    if auth.env_key == "SEC_USER_AGENT" and value.lower() == "ai-collect contact@example.com":
        return "missing"
    return "ok"


def runtime_key_status(auth: AuthConfig) -> AuthStatus:
    """Human-readable key readiness for show-platforms (optional unset keys -> missing)."""
    if not auth.env_key:
        return "not_required"
    value = os.getenv(auth.env_key, "").strip()
    if not value:
        return "missing"
    if auth.env_key == "SEC_USER_AGENT" and value.lower() == "ai-collect contact@example.com":
        return "missing"
    return "ok"


def _require_str(data: dict[str, Any], key: str, *, context: str) -> str:
    if key not in data or data[key] is None:
        raise ValueError(f"{context}: missing required field {key!r}")
    value = str(data[key]).strip()
    if not value:
        raise ValueError(f"{context}: required field {key!r} is empty")
    return value


def _optional_str(data: dict[str, Any], key: str) -> str | None:
    if key not in data or data[key] is None:
        return None
    value = str(data[key]).strip()
    return value or None


def _parse_auth(data: dict[str, Any], *, context: str) -> AuthConfig:
    if not isinstance(data, dict):
        raise ValueError(f"{context}: auth must be a mapping")
    env_key = str(data.get("env_key") or "").strip()
    required = bool(data.get("required", False))
    notes = _optional_str(data, "notes")
    return AuthConfig(env_key=env_key, required=required, notes=notes)


def _parse_loaders(rows: list[Any], path: Path) -> list[Loader]:
    if not isinstance(rows, list):
        raise ValueError(f"loaders must be a list in {path}")
    seen: set[str] = set()
    out: list[Loader] = []
    for i, row in enumerate(rows):
        ctx = f"loaders[{i}]"
        if not isinstance(row, dict):
            raise ValueError(f"{ctx}: must be a mapping")
        loader_id = _require_str(row, "id", context=ctx)
        if loader_id in seen:
            raise ValueError(f"{ctx}: duplicate loader id {loader_id!r}")
        seen.add(loader_id)
        out.append(
            Loader(
                id=loader_id,
                display_name=_require_str(row, "display_name", context=ctx),
                vendor=_require_str(row, "vendor", context=ctx),
                api_base_url=_require_str(row, "api_base_url", context=ctx),
                auth=_parse_auth(row.get("auth") or {}, context=f"{ctx}.auth"),
                phase=int(row.get("phase", 1)),
                enabled=bool(row.get("enabled", True)),
                cost_model=_require_str(row, "cost_model", context=ctx),
                rate_limit_notes=_optional_str(row, "rate_limit_notes"),
                cli_command=_optional_str(row, "cli_command"),
                notes=_optional_str(row, "notes"),
            )
        )
    return out


def _parse_platforms(rows: list[Any], path: Path) -> list[Platform]:
    if not isinstance(rows, list):
        raise ValueError(f"platforms must be a list in {path}")
    seen: set[str] = set()
    out: list[Platform] = []
    for i, row in enumerate(rows):
        ctx = f"platforms[{i}]"
        if not isinstance(row, dict):
            raise ValueError(f"{ctx}: must be a mapping")
        platform_id = _require_str(row, "id", context=ctx)
        if platform_id in seen:
            raise ValueError(f"{ctx}: duplicate platform id {platform_id!r}")
        seen.add(platform_id)
        collector = _require_str(row, "collector", context=ctx)
        phase = int(row.get("phase", 1))
        enabled = bool(row.get("enabled", True))
        if enabled and phase == 1 and collector not in KNOWN_COLLECTOR_NAMES:
            raise ValueError(
                f"{ctx}: phase 1 enabled platform {platform_id!r} references unknown "
                f"collector {collector!r}; implement collector or set phase>=2"
            )
        category = _require_str(row, "source_category", context=ctx)
        if category not in _ALLOWED_CATEGORIES:
            raise ValueError(f"{ctx}: invalid source_category {category!r}")
        reliability = _require_str(row, "source_reliability", context=ctx)
        if reliability not in _ALLOWED_RELIABILITY:
            raise ValueError(f"{ctx}: invalid source_reliability {reliability!r}")
        confidence = float(row.get("confidence_initial", 0.0))
        if not 0.0 <= confidence <= 1.0:
            raise ValueError(f"{ctx}: confidence_initial must be between 0 and 1, got {confidence}")
        out.append(
            Platform(
                id=platform_id,
                collector=collector,
                cli_source=_require_str(row, "cli_source", context=ctx),
                source_type=_require_str(row, "source_type", context=ctx),
                display_name=_require_str(row, "display_name", context=ctx),
                vendor=_require_str(row, "vendor", context=ctx),
                api_base_url=str(row.get("api_base_url") or "").strip(),
                auth=_parse_auth(row.get("auth") or {}, context=f"{ctx}.auth"),
                phase=phase,
                enabled=enabled,
                cost_model=_require_str(row, "cost_model", context=ctx),
                source_category=category,
                source_reliability=reliability,
                confidence_initial=confidence,
                rate_limit_notes=_optional_str(row, "rate_limit_notes"),
                reprocessable=bool(row.get("reprocessable", False)),
                collector_version=_optional_str(row, "collector_version"),
                notes=_optional_str(row, "notes"),
            )
        )
    return out
