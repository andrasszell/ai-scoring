from evidence_collection.db import apply_migrations, connect, current_version
from evidence_collection.db.migrations import MIGRATIONS


def test_migrations_apply_and_are_idempotent(tmp_path):
    c = connect(tmp_path / "m.sqlite")
    applied = apply_migrations(c)
    latest = max(v for v, _, _ in MIGRATIONS)
    assert current_version(c) == latest
    assert applied == [v for v, _, _ in MIGRATIONS]
    assert apply_migrations(c) == []
    assert current_version(c) == latest
    cols = {r["name"] for r in c.execute("PRAGMA table_info(collector_status)")}
    assert "source_hits" in cols
    assert "candidates_after_filter" in cols
    c.close()


def test_expected_tables_exist(conn):
    names = {
        r["name"]
        for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    for table in [
        "companies", "company_aliases", "documents", "evidence_items",
        "raw_api_responses", "collector_runs", "collector_status", "collection_metrics",
    ]:
        assert table in names
