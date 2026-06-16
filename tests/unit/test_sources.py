from pathlib import Path

import pytest

from evidence_collection.registry_gate import reset_registry_cache
from evidence_collection.sources import Reliability, SourceCategory, profile_for

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
MINIMAL = FIXTURES / "platforms_minimal.yaml"


@pytest.fixture(autouse=True)
def _clear_registry_cache():
    reset_registry_cache()
    yield
    reset_registry_cache()


def test_profile_for_reads_sec_metadata_from_registry():
    profile = profile_for("sec_annual_filing")
    assert profile.category == SourceCategory.REGULATORY_FILING
    assert profile.reliability == Reliability.HIGH
    assert profile.confidence_initial == 0.75


def test_profile_for_uses_registry_fixture(monkeypatch):
    monkeypatch.setenv("PLATFORMS_YAML", str(MINIMAL))
    profile = profile_for("sec_annual_filing")
    assert profile.category == SourceCategory.REGULATORY_FILING
    assert profile.confidence_initial == 0.75


def test_profile_for_prefers_phase1_enabled_over_later_phases(tmp_path, monkeypatch):
    path = tmp_path / "precedence.yaml"
    path.write_text(
        """
registry_version: "1"
loaders: []
platforms:
  - id: phase3_job
    collector: lightcast_hiring
    cli_source: lightcast
    source_type: job_posting
    display_name: Phase 3
    vendor: Lightcast
    api_base_url: ""
    auth:
      env_key: LIGHTCAST_API_KEY
      required: true
    phase: 3
    enabled: true
    cost_model: paid
    source_category: job_posting
    source_reliability: low
    confidence_initial: 0.99
  - id: phase1_job
    collector: hiring_jobs
    cli_source: hiring
    source_type: job_posting
    display_name: Phase 1
    vendor: SerpAPI
    api_base_url: https://serpapi.com
    auth:
      env_key: SERPAPI_API_KEY
      required: false
    phase: 1
    enabled: true
    cost_model: paid
    source_category: job_posting
    source_reliability: medium
    confidence_initial: 0.50
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("PLATFORMS_YAML", str(path))
    profile = profile_for("job_posting")
    assert profile.reliability == Reliability.MEDIUM
    assert profile.confidence_initial == 0.50


def test_profile_for_fallback_when_registry_missing(monkeypatch, tmp_path):
    missing = tmp_path / "missing.yaml"
    monkeypatch.setenv("PLATFORMS_YAML", str(missing))
    profile = profile_for("research_paper")
    assert profile.category == SourceCategory.THIRD_PARTY_DATABASE
    assert profile.confidence_initial == 0.45
