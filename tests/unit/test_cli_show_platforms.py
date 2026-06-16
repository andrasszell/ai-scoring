from pathlib import Path

import pytest

from evidence_collection.cli import cmd_show_platforms, format_platforms_table, main
from evidence_collection.platforms import AuthConfig, runtime_key_status
from evidence_collection.registry_gate import reset_registry_cache

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
MINIMAL = FIXTURES / "platforms_minimal.yaml"


@pytest.fixture(autouse=True)
def _clear_registry_cache():
    reset_registry_cache()
    yield
    reset_registry_cache()


def _args(**kwargs):
    defaults = {"phase": None, "all": False}
    defaults.update(kwargs)
    return type("Args", (), defaults)()


def test_runtime_key_status_marks_unset_optional_key_missing(monkeypatch):
    monkeypatch.delenv("FMP_API_KEY", raising=False)
    auth = AuthConfig(env_key="FMP_API_KEY", required=False)
    assert runtime_key_status(auth) == "missing"


def test_show_platforms_runs_without_db(capsys, monkeypatch):
    monkeypatch.setenv("PLATFORMS_YAML", str(MINIMAL))
    main(["--log-level", "ERROR", "show-platforms"])
    out = capsys.readouterr().out
    assert "active_phase1" in out
    assert "sec_filings" in out
    assert "KEY_STATUS" in out


def test_show_platforms_default_excludes_disabled(capsys, monkeypatch):
    monkeypatch.setenv("PLATFORMS_YAML", str(MINIMAL))
    cmd_show_platforms(_args())
    out = capsys.readouterr().out
    assert "active_phase1" in out
    assert "disabled_phase1" not in out
    assert "1 platform(s)" in out


def test_show_platforms_all_includes_disabled_and_later_phases(capsys, monkeypatch):
    monkeypatch.setenv("PLATFORMS_YAML", str(MINIMAL))
    cmd_show_platforms(_args(all=True))
    out = capsys.readouterr().out
    assert "active_phase1" in out
    assert "disabled_phase1" in out
    assert "active_phase2" in out
    assert "disabled_phase3" in out
    assert "4 platform(s)" in out


def test_show_platforms_all_lists_phase2_and_phase3_stubs(capsys):
    cmd_show_platforms(_args(all=True))
    out = capsys.readouterr().out
    for platform_id in ("github_repos", "press_releases", "product_documentation", "lightcast", "alphasense", "revelio"):
        assert platform_id in out
    assert out.count(" no ") >= 6


def test_show_platforms_phase_filter(capsys, monkeypatch):
    monkeypatch.setenv("PLATFORMS_YAML", str(MINIMAL))
    cmd_show_platforms(_args(phase=2, all=True))
    out = capsys.readouterr().out
    assert "active_phase2" in out
    assert "active_phase1" not in out


def test_format_platforms_table_columns():
    from evidence_collection.platforms import Platform

    platform = Platform(
        id="sec_edgar",
        collector="sec_filings",
        cli_source="sec",
        source_type="sec_annual_filing",
        display_name="SEC",
        vendor="U.S. SEC",
        api_base_url="https://data.sec.gov",
        auth=AuthConfig(env_key="SEC_USER_AGENT", required=True),
        phase=1,
        enabled=True,
        cost_model="free",
        source_category="regulatory_filing",
        source_reliability="high",
        confidence_initial=0.75,
    )
    text = format_platforms_table([platform], registry_version="1.0")
    assert "sec_edgar" in text
    assert "SEC_USER_AGENT" in text
    assert "free" in text
