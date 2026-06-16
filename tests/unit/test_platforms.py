from pathlib import Path

import pytest

from evidence_collection.platforms import AuthConfig, auth_status, load_registry

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
MINIMAL = FIXTURES / "platforms_minimal.yaml"
INVALID = FIXTURES / "platforms_invalid.yaml"
PRODUCTION = Path(__file__).resolve().parents[2] / "config" / "platforms.yaml"


def test_load_minimal_fixture():
    registry = load_registry(MINIMAL)
    assert registry.registry_version == "test-1.0"
    assert len(registry.loaders) == 1
    assert len(registry.platforms) == 4
    assert registry.platform_by_collector("sec_filings") is not None
    assert registry.platform_by_collector("sec_filings").id == "active_phase1"


def test_load_production_registry():
    registry = load_registry(PRODUCTION)
    enabled = registry.platforms_enabled(phase=1)
    assert len(enabled) >= 6
    ids = {p.id for p in enabled}
    assert "sec_edgar" in ids
    assert "semantic_scholar" in ids


def test_rejects_duplicate_id():
    with pytest.raises(ValueError, match="duplicate platform id 'dup_id'"):
        load_registry(INVALID)


def test_rejects_missing_required_field(tmp_path):
    path = tmp_path / "incomplete.yaml"
    path.write_text(
        """
registry_version: "1"
loaders: []
platforms:
  - id: incomplete
    collector: sec_filings
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="missing required field"):
        load_registry(path)


def test_rejects_invalid_confidence(tmp_path):
    path = tmp_path / "bad_confidence.yaml"
    path.write_text(
        """
registry_version: "1"
loaders: []
platforms:
  - id: bad
    collector: sec_filings
    cli_source: sec
    source_type: sec_annual_filing
    display_name: X
    vendor: SEC
    api_base_url: https://data.sec.gov
    auth:
      env_key: SEC_USER_AGENT
      required: true
    phase: 1
    enabled: true
    cost_model: free
    source_category: regulatory_filing
    source_reliability: high
    confidence_initial: 1.5
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="confidence_initial"):
        load_registry(path)


def test_platforms_enabled_excludes_disabled():
    registry = load_registry(MINIMAL)
    enabled = registry.platforms_enabled(phase=None)
    ids = {p.id for p in enabled}
    assert "active_phase1" in ids
    assert "active_phase2" in ids
    assert "disabled_phase1" not in ids
    assert "disabled_phase3" not in ids


def test_platforms_enabled_phase1_excludes_later_phases():
    registry = load_registry(MINIMAL)
    phase1 = registry.platforms_enabled(phase=1)
    ids = {p.id for p in phase1}
    assert ids == {"active_phase1"}


def test_auth_status_missing_when_required_env_empty(monkeypatch):
    registry = load_registry(MINIMAL)
    platform = registry.platform_by_id("active_phase1")
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    assert registry.auth_status(platform) == "missing"
    assert auth_status(platform.auth) == "missing"


def test_auth_status_ok_when_env_set(monkeypatch):
    registry = load_registry(MINIMAL)
    platform = registry.platform_by_id("active_phase1")
    monkeypatch.setenv("SEC_USER_AGENT", "TestBot test@example.com")
    assert registry.auth_status(platform) == "ok"


def test_auth_status_not_required_when_auth_optional():
    registry = load_registry(MINIMAL)
    platform = registry.platform_by_id("disabled_phase1")
    assert platform.auth.required is False
    assert registry.auth_status(platform) == "not_required"


def test_auth_status_not_required_without_env_key():
    auth = AuthConfig(env_key="", required=True)
    assert auth_status(auth) == "not_required"
