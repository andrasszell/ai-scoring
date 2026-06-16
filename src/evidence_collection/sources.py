from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

# Source quality model (Coding Standards §6). The collection layer classifies a
# source and assigns a *prior* reliability and initial confidence. This is NOT
# scoring or interpretation of meaning — it is source provenance metadata the
# inference layer needs to weigh evidence. The inference layer is free to override.


class SourceCategory:
    OFFICIAL_COMPANY = "official_company"
    REGULATORY_FILING = "regulatory_filing"
    JOB_POSTING = "job_posting"
    PRESS_RELEASE = "press_release"
    TECHNICAL_BLOG = "technical_blog"
    PRODUCT_DOCUMENTATION = "product_documentation"
    NEWS_ARTICLE = "news_article"
    THIRD_PARTY_DATABASE = "third_party_database"
    SOCIAL_MEDIA = "social_media"
    UNKNOWN = "unknown"


class Reliability:
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class SourceProfile:
    category: str
    reliability: str
    confidence_initial: float


# Fallback when registry is unavailable or has no entry for a source_type.
_PROFILES: dict[str, SourceProfile] = {
    "sec_annual_filing": SourceProfile(SourceCategory.REGULATORY_FILING, Reliability.HIGH, 0.75),
    "earnings_call_transcript": SourceProfile(SourceCategory.OFFICIAL_COMPANY, Reliability.HIGH, 0.70),
    "web_search_product": SourceProfile(SourceCategory.NEWS_ARTICLE, Reliability.LOW, 0.40),
    "job_posting": SourceProfile(SourceCategory.JOB_POSTING, Reliability.MEDIUM, 0.50),
    "patent": SourceProfile(SourceCategory.REGULATORY_FILING, Reliability.MEDIUM, 0.55),
    "research_paper": SourceProfile(SourceCategory.THIRD_PARTY_DATABASE, Reliability.MEDIUM, 0.45),
    "github_repository": SourceProfile(SourceCategory.THIRD_PARTY_DATABASE, Reliability.MEDIUM, 0.50),
    "press_release": SourceProfile(SourceCategory.PRESS_RELEASE, Reliability.MEDIUM, 0.45),
    "product_documentation": SourceProfile(
        SourceCategory.PRODUCT_DOCUMENTATION, Reliability.HIGH, 0.65
    ),
}

_DEFAULT = SourceProfile(SourceCategory.UNKNOWN, Reliability.UNKNOWN, 0.30)

_REGISTRY_INDEX: dict[str, SourceProfile] | None = None


def reset_profile_cache() -> None:
    """Clear cached registry profiles (for tests)."""
    global _REGISTRY_INDEX
    _REGISTRY_INDEX = None


def _platform_precedence(platform) -> tuple[int, int, int]:
    """Rank platforms sharing a source_type; higher wins."""
    return (
        1 if platform.enabled else 0,
        1 if platform.phase == 1 else 0,
        -platform.phase,
    )


def _build_registry_index() -> dict[str, SourceProfile]:
    try:
        from .platforms import load_registry

        registry = load_registry()
    except (FileNotFoundError, ValueError, OSError):
        return {}
    best: dict[str, tuple[tuple[int, int, int], SourceProfile]] = {}
    for platform in registry.platforms:
        profile = SourceProfile(
            platform.source_category,
            platform.source_reliability,
            platform.confidence_initial,
        )
        rank = _platform_precedence(platform)
        prev = best.get(platform.source_type)
        if prev is None or rank > prev[0]:
            best[platform.source_type] = (rank, profile)
    return {source_type: profile for source_type, (_, profile) in best.items()}


def _registry_profiles() -> dict[str, SourceProfile]:
    global _REGISTRY_INDEX
    if _REGISTRY_INDEX is None:
        _REGISTRY_INDEX = _build_registry_index()
    return _REGISTRY_INDEX


def profile_for(source_type: str) -> SourceProfile:
    """Return source metadata from config/platforms.yaml, with code fallback."""
    return _registry_profiles().get(source_type) or _PROFILES.get(source_type, _DEFAULT)


def refine_for_url(profile: SourceProfile, url: str | None, website_domain: str | None) -> SourceProfile:
    """Upgrade a profile to official_company when the evidence URL is on the
    company's own domain (Coding Standards §6 per-domain refinement).

    Example: a Google result whose link is microsoft.com is a first-party claim,
    not a third-party news article, so it earns higher reliability.
    """
    if not url or not website_domain:
        return profile
    netloc = urlparse(url).netloc.lower().removeprefix("www.")
    domain = website_domain.lower().removeprefix("www.").strip()
    if domain and (netloc == domain or netloc.endswith("." + domain)):
        return SourceProfile(
            SourceCategory.OFFICIAL_COMPANY,
            Reliability.HIGH,
            max(profile.confidence_initial, 0.70),
        )
    return profile
