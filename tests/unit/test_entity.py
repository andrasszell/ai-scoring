from evidence_collection.universe.entity import (
    clean_company_name,
    match_rows,
    search_name,
)

ROWS = [
    {"ticker": "AAPL", "company_name": "Apple Inc."},
    {"ticker": "MSFT", "company_name": "Microsoft Corporation"},
    {"ticker": "GOOGL", "company_name": "Alphabet Inc. (Class A)"},
]


def test_clean_company_name_strips_suffixes_and_parens():
    assert clean_company_name("Apple Inc.") == "Apple"
    assert clean_company_name("Alphabet Inc. (Class A)") == "Alphabet"
    assert clean_company_name("Meta Platforms, Inc.") == "Meta Platforms"


def test_clean_company_name_falls_back_when_emptied():
    assert clean_company_name("Inc.") == "Inc."


def test_search_name_uses_brand_alias_by_ticker():
    assert search_name({"ticker": "GOOGL", "company_name": "Alphabet Inc."}) == "Google"
    assert search_name({"ticker": "META", "company_name": "Meta Platforms, Inc."}) == "Meta"


def test_search_name_falls_back_to_cleaned_name():
    assert search_name({"ticker": "MSFT", "company_name": "Microsoft Corporation"}) == "Microsoft"


def test_match_rows_exact_ticker():
    assert [r["ticker"] for r in match_rows(ROWS, "msft")] == ["MSFT"]


def test_match_rows_partial_name():
    assert [r["ticker"] for r in match_rows(ROWS, "alpha")] == ["GOOGL"]


def test_match_rows_no_match():
    assert match_rows(ROWS, "zzz") == []
