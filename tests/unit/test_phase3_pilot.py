from unittest.mock import patch

import pytest

from evidence_collection.universe.domains import load_company_domains
from evidence_collection.universe.pilot import (
    default_pilot_path,
    ensure_pilot_companies,
    load_pilot_entries,
    pilot_includes_validation,
    pilot_tickers,
)
from evidence_collection.universe.validation import validation_tickers


def test_default_pilot_path_exists():
    path = default_pilot_path()
    assert path.is_file()
    assert path.name == "phase3_pilot_companies.yaml"


def test_load_pilot_entries_has_50_tickers():
    entries = load_pilot_entries()
    tickers = pilot_tickers()
    assert len(entries) == 50
    assert len(tickers) == len(set(tickers))
    assert "NFLX" in tickers
    assert "CAT" in tickers


def test_pilot_includes_validation_set():
    assert pilot_includes_validation() is True
    pilot = set(pilot_tickers())
    for ticker in validation_tickers():
        assert ticker in pilot


def test_pilot_tickers_have_domains():
    domains = load_company_domains()
    missing = [t for t in pilot_tickers() if t not in domains]
    assert missing == []


def test_ensure_pilot_companies_uses_sec_fallback(conn, tmp_path):
    yaml_path = tmp_path / "pilot.yaml"
    yaml_path.write_text(
        "version: '1'\ncompanies:\n  - ticker: ELAN\n    group: sec_fallback\n",
        encoding="utf-8",
    )
    with patch(
        "evidence_collection.universe.pilot.fetch_sec_companies",
        return_value=[
            {
                "ticker": "ELAN",
                "company_name": "Elanco Animal Health Inc",
                "sector": None,
                "industry": None,
                "cik": "0001739104",
                "exchange": None,
                "country": "US",
                "source_of_identifier": "sec_company_tickers",
            }
        ],
    ):
        companies, tickers = ensure_pilot_companies(conn, path=yaml_path)
    assert tickers == ["ELAN"]
    assert companies[0]["website_domain"] == "elanco.com"
