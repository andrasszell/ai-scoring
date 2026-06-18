from __future__ import annotations

import sqlite3

from ..db import repository as repo
from .domains import load_company_domains
from .github_orgs import load_company_github_orgs
from .pilot import pilot_tickers


def universe_stats(conn: sqlite3.Connection) -> dict:
    """Aggregate universe coverage for Phase 3A.1 verification."""
    row = conn.execute(
        """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN cik IS NOT NULL AND cik != '' THEN 1 ELSE 0 END) AS with_cik,
            SUM(CASE WHEN website_domain IS NOT NULL AND website_domain != '' THEN 1 ELSE 0 END) AS with_domain
        FROM companies
        """
    ).fetchone()
    domains = load_company_domains()
    github = load_company_github_orgs()
    pilot = pilot_tickers()
    pilot_rows = repo.get_companies(conn, pilot)
    pilot_domains_db = sum(1 for c in pilot_rows if c.get("website_domain"))
    pilot_domains_cfg = sum(1 for t in pilot if t in domains)
    pilot_github = sum(1 for t in pilot if github.get(t))
    return {
        "total_companies": int(row["total"]),
        "with_cik": int(row["with_cik"] or 0),
        "with_domain_db": int(row["with_domain"] or 0),
        "domains_configured": len(domains),
        "github_orgs_configured": sum(1 for orgs in github.values() if orgs),
        "pilot_ticker_count": len(pilot),
        "pilot_with_domain_db": pilot_domains_db,
        "pilot_with_domain_config": pilot_domains_cfg,
        "pilot_with_github_orgs": pilot_github,
    }


def spot_check_tickers(conn: sqlite3.Connection, tickers: list[str]) -> list[dict]:
    """Return identity fields for manual spot-check (3A.1)."""
    companies = repo.get_companies(conn, tickers)
    by_ticker = {c["ticker"]: c for c in companies}
    out: list[dict] = []
    for ticker in tickers:
        company = by_ticker.get(ticker)
        if company is None:
            out.append({"ticker": ticker, "found": False})
            continue
        out.append(
            {
                "ticker": ticker,
                "found": True,
                "company_name": company.get("company_name"),
                "cik": company.get("cik"),
                "sector": company.get("sector"),
                "website_domain": company.get("website_domain"),
            }
        )
    return out


DEFAULT_SPOT_CHECK = ["MSFT", "JPM", "XOM", "WMT", "PLTR", "ELAN", "NFLX", "V", "ABBV", "CAT"]
