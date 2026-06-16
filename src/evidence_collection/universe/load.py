from __future__ import annotations

from ..db import repository as repo
from .aliases import seed_company_aliases
from .domains import apply_domains
from .sp500 import fetch_sp500_with_ciks


def load_universe(conn, *, limit: int | None = None) -> tuple[int, int]:
    """Load S&P 500 + CIKs, seed website domains and company aliases."""
    rows = fetch_sp500_with_ciks()
    if limit is not None:
        rows = rows[:limit]
    companies = repo.upsert_companies(conn, rows)
    aliases = seed_company_aliases(conn)
    return companies, aliases


def enrich_companies(conn, companies: list[dict]) -> list[dict]:
    """Backfill website_domain from config and persist when newly known."""
    if not companies:
        return companies
    enriched = apply_domains(companies)
    gained_domain = [
        row
        for before, row in zip(companies, enriched)
        if not before.get("website_domain") and row.get("website_domain")
    ]
    if gained_domain:
        repo.upsert_companies(conn, gained_domain)
    return enriched
