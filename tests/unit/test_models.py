import pytest

from evidence_collection.collectors import REGISTRY, SOURCE_KEYS, get_collectors
from evidence_collection.models import CollectorResult
from evidence_collection.status import CollectionStatus


def test_collector_result_rejects_unknown_status():
    with pytest.raises(ValueError):
        CollectorResult("not_a_real_status")


def test_collector_result_accepts_known_status():
    r = CollectorResult(CollectionStatus.NO_RESULTS)
    assert r.status == CollectionStatus.NO_RESULTS


def test_get_collectors_defaults_to_enabled_phase1():
    collectors = get_collectors()
    assert len(collectors) == 6
    assert {c.name for c in collectors} == {
        "sec_filings",
        "earnings_calls",
        "web_products",
        "hiring_jobs",
        "patents",
        "research",
    }


def test_get_collectors_selects_subset_in_order():
    chosen = get_collectors(["hiring", "sec"])
    assert [c.name for c in chosen] == ["hiring_jobs", "sec_filings"]


def test_get_collectors_rejects_unknown_source():
    with pytest.raises(ValueError):
        get_collectors(["nope"])


def test_every_collector_declares_name_version_source():
    for key in SOURCE_KEYS:
        c = REGISTRY[key]
        assert c.name and c.version and c.source_type


def test_every_active_collector_has_registry_platform_id():
    from evidence_collection.registry_gate import get_platform_registry

    registry = get_platform_registry()
    for collector in REGISTRY.values():
        assert collector.platform_id, f"{collector.name} missing platform_id"
        platform = registry.platform_by_id(collector.platform_id)
        assert platform is not None, collector.platform_id
        assert platform.collector == collector.name
        assert platform.enabled is True
        assert platform.phase == 1
