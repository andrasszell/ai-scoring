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


def test_get_collectors_defaults_to_all():
    assert len(get_collectors()) == len(REGISTRY)


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
