from evidence_collection.collectors.serpapi import ProductServiceCollector
from evidence_collection.db import repository as repo
from evidence_collection.universe.aliases import seed_company_aliases


def test_product_query_uses_db_alias(conn):
    repo.upsert_companies(
        conn,
        [
            {"ticker": "GOOGL", "company_name": "Alphabet Inc.", "company_id": "GOOGL"},
            {"ticker": "GOOG", "company_name": "Alphabet Inc. Class C", "company_id": "GOOG"},
        ],
    )
    seed_company_aliases(conn)
    collector = ProductServiceCollector()
    company = {"ticker": "GOOGL", "company_name": "Alphabet Inc."}
    # Build query the same way collect() does — must use DB alias, not "Alphabet".
    from evidence_collection.universe.entity import search_name

    assert search_name(company, conn=conn) == "Google"
    query_prefix = f'"{search_name(company, conn=conn)}"'
    assert query_prefix == '"Google"'
