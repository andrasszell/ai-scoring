from pathlib import Path

import pytest

from evidence_collection.universe.github_orgs import (
    github_orgs_for_ticker,
    load_company_github_orgs,
)


FIXTURE = Path(__file__).resolve().parents[2] / "config" / "company_github_orgs.yaml"


def test_load_company_github_orgs_includes_msft():
    mapping = load_company_github_orgs(FIXTURE)
    assert "MSFT" in mapping
    assert "microsoft" in mapping["MSFT"]


def test_github_orgs_for_ticker_normalizes_dots():
    mapping = {"BRK-B": ["berkshire"]}
    assert github_orgs_for_ticker("brk.b", mapping) == ["berkshire"]


def test_github_orgs_for_ticker_missing_returns_empty():
    assert github_orgs_for_ticker("ZZZZ", {}) == []


def test_load_rejects_non_list_orgs(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("MSFT: not-a-list\n", encoding="utf-8")
    with pytest.raises(ValueError, match="must be a list"):
        load_company_github_orgs(path)
