from unittest.mock import patch

from evidence_collection.db import repository as repo
from evidence_collection.universe.load import enrich_companies, load_universe


def test_load_universe_upserts_and_seeds_aliases(conn):
    rows = [
        {
            "ticker": "MSFT",
            "company_name": "Microsoft Corporation",
            "cik": "0000789019",
            "country": "US",
            "source_of_identifier": "test",
            "website_domain": "microsoft.com",
        },
        {
            "ticker": "GOOGL",
            "company_name": "Alphabet Inc.",
            "cik": "0001652044",
            "country": "US",
            "source_of_identifier": "test",
            "website_domain": "google.com",
        },
    ]
    with patch("evidence_collection.universe.load.fetch_sp500_with_ciks", return_value=rows):
        n, aliases = load_universe(conn)
    assert n == 2
    assert aliases >= 1
    assert repo.get_aliases(conn, "GOOGL")
    stored = {c["ticker"]: c for c in repo.get_companies(conn, ["MSFT", "GOOGL"])}
    assert stored["MSFT"]["website_domain"] == "microsoft.com"


def test_enrich_companies_backfills_missing_domain(conn):
    repo.upsert_companies(
        conn,
        [{"ticker": "MSFT", "company_name": "Microsoft Corporation", "company_id": "MSFT"}],
    )
    companies = repo.get_companies(conn, ["MSFT"])
    enriched = enrich_companies(conn, companies)
    assert enriched[0]["website_domain"] == "microsoft.com"
    reloaded = repo.get_companies(conn, ["MSFT"])[0]
    assert reloaded["website_domain"] == "microsoft.com"
