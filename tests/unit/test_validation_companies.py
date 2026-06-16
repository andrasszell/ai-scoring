import pytest

from evidence_collection.universe.validation import (
    default_validation_path,
    ensure_validation_companies,
    load_validation_entries,
    validation_tickers,
)


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


def test_ensure_validation_companies_uses_sec_fallback(conn):
    entries = load_validation_entries()
    sec_fallback = [e["ticker"] for e in entries if e["group"] == "sec_fallback"]
    assert sec_fallback
    companies, tickers = ensure_validation_companies(conn)
    assert len(companies) == len(tickers) == 35
    found = {c["ticker"] for c in companies}
    for ticker in sec_fallback:
        assert ticker in found
        row = next(c for c in companies if c["ticker"] == ticker)
        assert row.get("cik")


def test_ensure_validation_companies_raises_for_unknown_ticker(conn, tmp_path):
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text(
        "version: '1'\ncompanies:\n  - ticker: NOTAREALTICKERXYZ\n    group: test\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="NOTAREALTICKERXYZ"):
        ensure_validation_companies(conn, path=bad_yaml)
