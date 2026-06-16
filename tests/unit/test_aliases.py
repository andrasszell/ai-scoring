from pathlib import Path

import pytest

from evidence_collection.db import repository as repo
from evidence_collection.universe.aliases import load_company_aliases, seed_company_aliases
from evidence_collection.universe.entity import search_name

FIXTURE = Path(__file__).resolve().parents[2] / "config" / "company_aliases.yaml"


def test_load_company_aliases_includes_required_tickers():
    rows = load_company_aliases(FIXTURE)
    tickers = {r["ticker"] for r in rows}
    assert {"GOOGL", "META", "AMZN"}.issubset(tickers)


def test_search_name_uses_db_alias_when_conn_provided(conn):
    repo.upsert_companies(
        conn,
        [
            {"ticker": "GOOGL", "company_name": "Alphabet Inc.", "company_id": "GOOGL"},
            {"ticker": "GOOG", "company_name": "Alphabet Inc. Class C", "company_id": "GOOG"},
        ],
    )
    seed_company_aliases(conn, FIXTURE)
    name = search_name({"ticker": "GOOGL", "company_name": "Alphabet Inc."}, conn=conn)
    assert name == "Google"


def test_search_name_falls_back_without_conn():
    assert search_name({"ticker": "GOOGL", "company_name": "Alphabet Inc."}) == "Google"
