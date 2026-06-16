from evidence_collection.cli import format_company_identity_report
from evidence_collection.db import repository as repo
from evidence_collection.universe.domains import apply_domains


def test_format_company_identity_report(conn):
    rows = apply_domains(
        [
            {
                "ticker": "MSFT",
                "company_name": "Microsoft Corporation",
                "sector": "Technology",
                "cik": "0000789019",
                "company_id": "MSFT",
            }
        ]
    )
    repo.upsert_companies(conn, rows)
    repo.insert_alias(conn, "MSFT", "Microsoft", "brand", "test")

    text = format_company_identity_report(conn, "MSFT")

    assert "MSFT — Microsoft Corporation" in text
    assert "microsoft.com" in text
    assert "Technology" in text
    assert "0000789019" in text
    assert "Microsoft (brand)" in text
    assert "(none — run ai-collect collect)" in text
