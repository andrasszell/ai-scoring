from __future__ import annotations

from io import StringIO

import pandas as pd

from ..http import get

WIKI_SP500 = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
SEC_TICKERS = "https://www.sec.gov/files/company_tickers.json"


def normalize_ticker(ticker: str) -> str:
    return ticker.replace(".", "-").strip().upper()


def fetch_sp500() -> list[dict]:
    # Fetch via the shared helper so we send a descriptive User-Agent. Wikipedia
    # returns HTTP 403 to pandas' default urllib User-Agent.
    html = get(WIKI_SP500).text
    tables = pd.read_html(StringIO(html))
    df = tables[0].rename(
        columns={
            "Symbol": "ticker",
            "Security": "company_name",
            "GICS Sector": "sector",
            "GICS Sub-Industry": "industry",
        }
    )
    rows = []
    for _, r in df.iterrows():
        rows.append(
            {
                "ticker": normalize_ticker(str(r["ticker"])),
                "company_name": str(r["company_name"]),
                "sector": str(r.get("sector", "")) or None,
                "industry": str(r.get("industry", "")) or None,
                "cik": None,
                "exchange": None,
                "country": "US",
                "source_of_identifier": "wikipedia_sp500",
            }
        )
    return rows


def fetch_sec_ticker_map() -> dict[str, str]:
    data = get(SEC_TICKERS, sec=True).json()
    mapping: dict[str, str] = {}
    for item in data.values():
        mapping[normalize_ticker(item["ticker"])] = str(item["cik_str"]).zfill(10)
    return mapping


def fetch_sec_companies() -> list[dict]:
    """All SEC-registered filers (ticker, name, CIK).

    Much broader than the S&P 500 universe; used as a fallback so any listed
    company can be analyzed by name even if it isn't an index constituent.
    """
    data = get(SEC_TICKERS, sec=True).json()
    rows = []
    for item in data.values():
        rows.append(
            {
                "ticker": normalize_ticker(item["ticker"]),
                "company_name": str(item["title"]),
                "sector": None,
                "industry": None,
                "cik": str(item["cik_str"]).zfill(10),
                "exchange": None,
                "country": "US",
                "source_of_identifier": "sec_company_tickers",
            }
        )
    return rows


def fetch_sp500_with_ciks() -> list[dict]:
    from .domains import apply_domains

    rows = fetch_sp500()
    cik_map = fetch_sec_ticker_map()
    for row in rows:
        row["cik"] = cik_map.get(row["ticker"])
    return apply_domains(rows)
