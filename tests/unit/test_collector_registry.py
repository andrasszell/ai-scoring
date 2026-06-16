import pytest

from evidence_collection.collectors import REGISTRY, get_collectors
from evidence_collection.collectors.serpapi import ProductServiceCollector
from evidence_collection.db import repository as repo
from evidence_collection.registry_gate import (
    api_key_missing_result,
    collector_gate,
    reset_registry_cache,
)
from evidence_collection.runner import run_collection
from evidence_collection.status import CollectionStatus


@pytest.fixture(autouse=True)
def _clear_registry_cache():
    reset_registry_cache()
    yield
    reset_registry_cache()


def test_get_collectors_defaults_to_enabled_platforms():
    collectors = get_collectors()
    assert len(collectors) == 9
    assert {c.name for c in collectors} == {
        "sec_filings",
        "earnings_calls",
        "web_products",
        "hiring_jobs",
        "patents",
        "research",
        "github_repos",
        "press_releases",
        "product_docs",
    }


def test_get_collectors_explicit_includes_disabled_platform(tmp_path, monkeypatch):
    path = tmp_path / "gate.yaml"
    path.write_text(
        """
registry_version: "1"
loaders: []
platforms:
  - id: sec_edgar
    collector: sec_filings
    cli_source: sec
    source_type: sec_annual_filing
    display_name: SEC
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
    confidence_initial: 0.75
  - id: serpapi_web
    collector: web_products
    cli_source: products
    source_type: web_search_product
    display_name: SerpAPI web
    vendor: SerpAPI
    api_base_url: https://serpapi.com
    auth:
      env_key: SERPAPI_API_KEY
      required: false
    phase: 1
    enabled: false
    cost_model: paid
    source_category: news_article
    source_reliability: low
    confidence_initial: 0.40
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("PLATFORMS_YAML", str(path))
    assert get_collectors() == [REGISTRY["sec"]]
    assert get_collectors(["products"]) == [REGISTRY["products"]]


def test_collector_gate_skips_disabled_platform(tmp_path, monkeypatch):
    path = tmp_path / "gate.yaml"
    path.write_text(
        """
registry_version: "1"
loaders: []
platforms:
  - id: serpapi_web
    collector: web_products
    cli_source: products
    source_type: web_search_product
    display_name: SerpAPI web
    vendor: SerpAPI
    api_base_url: https://serpapi.com
    auth:
      env_key: SERPAPI_API_KEY
      required: false
    phase: 1
    enabled: false
    cost_model: paid
    source_category: news_article
    source_reliability: low
    confidence_initial: 0.40
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("PLATFORMS_YAML", str(path))
    collector = ProductServiceCollector()
    result = collector_gate(collector)
    assert result is not None
    assert result.status == CollectionStatus.SKIPPED
    assert result.message == "platform_disabled:serpapi_web"


def test_api_key_missing_message_from_registry():
    collector = ProductServiceCollector()
    result = api_key_missing_result(collector)
    assert result.status == CollectionStatus.API_KEY_MISSING
    assert result.message == "missing_serpapi_api_key"


def test_runner_records_skipped_for_disabled_platform(conn, tmp_path, monkeypatch):
    path = tmp_path / "gate.yaml"
    path.write_text(
        """
registry_version: "1"
loaders: []
platforms:
  - id: serpapi_web
    collector: web_products
    cli_source: products
    source_type: web_search_product
    display_name: SerpAPI web
    vendor: SerpAPI
    api_base_url: https://serpapi.com
    auth:
      env_key: SERPAPI_API_KEY
      required: false
    phase: 1
    enabled: false
    cost_model: paid
    source_category: news_article
    source_reliability: low
    confidence_initial: 0.40
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("PLATFORMS_YAML", str(path))
    repo.upsert_companies(conn, [{"ticker": "MSFT", "company_name": "Microsoft Corporation"}])
    company = repo.get_companies(conn, ["MSFT"])[0]
    run_collection(
        conn,
        [company],
        [ProductServiceCollector()],
        command="test",
        args={},
    )
    summary = {r["source_type"]: r for r in repo.status_summary(conn, ["MSFT"])}
    assert summary["web_search_product"]["status"] == CollectionStatus.SKIPPED
