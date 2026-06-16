from unittest.mock import patch

import pytest

from evidence_collection.universe.domains import load_company_domains
from evidence_collection.universe.validation import (
    default_validation_path,
    ensure_validation_companies,
    load_validation_entries,
    validation_tickers,
)

ELAN_SEC_ROW = {
    "ticker": "ELAN",
    "company_name": "Elanco Animal Health Inc",
    "sector": None,
    "industry": None,
    "cik": "0001739104",
    "exchange": None,
    "country": "US",
    "source_of_identifier": "sec_company_tickers",
}


def test_default_validation_path_exists():
    path = default_validation_path()
    assert path.is_file()
    assert path.name == "validation_companies.yaml"


def test_load_validation_entries_has_35_tickers():
    entries = load_validation_entries()
    tickers = validation_tickers()
    assert len(entries) == 35
    assert len(tickers) == len(set(tickers))
    groups = {e["group"] for e in entries}
    assert "mega_cap_default" in groups
    assert "sec_fallback" in groups


def test_validation_tickers_include_default_and_sec_fallback():
    tickers = validation_tickers()
    assert "MSFT" in tickers
    assert "ELAN" in tickers
    assert "PLTR" in tickers


def test_validation_tickers_have_domains():
    domains = load_company_domains()
    missing = [t for t in validation_tickers() if t not in domains]
    assert missing == []


def test_ensure_validation_companies_uses_sec_fallback(conn, tmp_path):
    yaml_path = tmp_path / "val.yaml"
    yaml_path.write_text(
        "version: '1'\ncompanies:\n  - ticker: ELAN\n    group: sec_fallback\n",
        encoding="utf-8",
    )
    with patch(
        "evidence_collection.universe.validation.fetch_sec_companies",
        return_value=[ELAN_SEC_ROW],
    ):
        companies, tickers = ensure_validation_companies(conn, path=yaml_path)
    assert tickers == ["ELAN"]
    assert len(companies) == 1
    assert companies[0]["ticker"] == "ELAN"
    assert companies[0]["cik"] == "0001739104"
    assert companies[0]["website_domain"] == "elanco.com"


def test_ensure_validation_companies_raises_for_unknown_ticker(conn, tmp_path):
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text(
        "version: '1'\ncompanies:\n  - ticker: NOTAREALTICKERXYZ\n    group: test\n",
        encoding="utf-8",
    )
    with patch("evidence_collection.universe.validation.fetch_sec_companies", return_value=[]):
        with pytest.raises(ValueError, match="NOTAREALTICKERXYZ"):
            ensure_validation_companies(conn, path=bad_yaml)
