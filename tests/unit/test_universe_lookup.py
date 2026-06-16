import pytest

from evidence_collection.universe.lookup import (
    CompanyAmbiguousError,
    CompanyNotFoundError,
    ensure_single_company,
    format_ambiguous_message,
    lookup_company,
    upsert_tickers_from_sec,
)


ELAN_SEC = {
    "ticker": "ELAN",
    "company_name": "Elanco Animal Health Inc",
    "cik": "0001739104",
    "sector": None,
    "industry": None,
    "exchange": None,
    "country": "US",
    "source_of_identifier": "sec_company_tickers",
}


def test_lookup_company_finds_db_row(conn):
    from evidence_collection.db import repository as repo

    repo.upsert_companies(conn, [{"ticker": "MSFT", "company_name": "Microsoft Corporation"}])
    result = lookup_company(conn, "MSFT")
    assert not result.used_sec_fallback
    assert result.matches[0]["ticker"] == "MSFT"


def test_lookup_company_sec_fallback(monkeypatch, conn):
    monkeypatch.setattr(
        "evidence_collection.universe.lookup.fetch_sec_companies",
        lambda: [ELAN_SEC],
    )
    result = lookup_company(conn, "ELAN")
    assert result.used_sec_fallback
    assert result.matches[0]["ticker"] == "ELAN"


def test_ensure_single_company_ambiguous(conn):
    from evidence_collection.db import repository as repo

    repo.upsert_companies(conn, [
        {"ticker": "ABC", "company_name": "Alpha Beta Corp"},
        {"ticker": "ABD", "company_name": "Alpha Beta Devices"},
    ])
    with pytest.raises(CompanyAmbiguousError):
        ensure_single_company(conn, "Alpha Beta", upsert=False)


def test_format_ambiguous_message_lists_candidates():
    msg = format_ambiguous_message("Alpha", [{"ticker": "A", "company_name": "Alpha One"}])
    assert "A:" in msg
    assert "more specific" in msg


def test_upsert_tickers_from_sec(monkeypatch, conn):
    from evidence_collection.db import repository as repo

    monkeypatch.setattr(
        "evidence_collection.universe.lookup.fetch_sec_companies",
        lambda: [ELAN_SEC],
    )
    added, missing = upsert_tickers_from_sec(conn, ["ELAN", "ZZZZ"])
    assert len(added) == 1
    assert added[0]["ticker"] == "ELAN"
    assert missing == ["ZZZZ"]
    rows = repo.get_companies(conn, ["ELAN"])
    assert rows[0]["cik"] == "0001739104"


def test_ensure_single_company_not_found(monkeypatch, conn):
    monkeypatch.setattr(
        "evidence_collection.universe.lookup.fetch_sec_companies",
        lambda: [],
    )
    with pytest.raises(CompanyNotFoundError):
        ensure_single_company(conn, "No Such Co", upsert=False)
