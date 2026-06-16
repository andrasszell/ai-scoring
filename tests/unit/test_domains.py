from pathlib import Path

import pytest

from evidence_collection.config import DEFAULT_TICKERS
from evidence_collection.universe.domains import (
    apply_domains,
    default_tickers_have_domains,
    load_company_domains,
)

FIXTURE = Path(__file__).resolve().parents[2] / "config" / "company_domains.yaml"


def test_load_company_domains_includes_default_tickers():
    domains = load_company_domains(FIXTURE)
    assert default_tickers_have_domains(domains)
    assert domains["MSFT"] == "microsoft.com"


def test_apply_domains_sets_website_domain_when_missing():
    rows = apply_domains(
        [{"ticker": "MSFT", "company_name": "Microsoft Corporation"}],
        {"MSFT": "microsoft.com"},
    )
    assert rows[0]["website_domain"] == "microsoft.com"


def test_apply_domains_does_not_overwrite_existing():
    rows = apply_domains(
        [{"ticker": "MSFT", "website_domain": "custom.example"}],
        {"MSFT": "microsoft.com"},
    )
    assert rows[0]["website_domain"] == "custom.example"


def test_all_default_tickers_present_in_config():
    domains = load_company_domains(FIXTURE)
    missing = [t for t in DEFAULT_TICKERS if t not in domains]
    assert missing == []
