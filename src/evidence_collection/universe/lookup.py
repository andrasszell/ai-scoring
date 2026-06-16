from __future__ import annotations

from dataclasses import dataclass

from ..db import repository as repo
from .domains import apply_domains
from .entity import match_rows, resolve_company
from .load import enrich_companies
from .sp500 import fetch_sec_companies, normalize_ticker


class CompanyNotFoundError(ValueError):
    """No company matched the query in the DB or SEC filer list."""

    def __init__(self, query: str) -> None:
        self.query = query
        super().__init__(f"No company matches {query!r}. Try the exact ticker symbol.")


class CompanyAmbiguousError(ValueError):
    """Multiple companies matched the query."""

    def __init__(self, query: str, matches: list[dict]) -> None:
        self.query = query
        self.matches = matches
        super().__init__(format_ambiguous_message(query, matches))


@dataclass(frozen=True)
class CompanyLookupResult:
    matches: list[dict]
    used_sec_fallback: bool


def format_ambiguous_message(query: str, matches: list[dict]) -> str:
    listing = "\n".join(
        f"  - {m['ticker']}: {m.get('company_name') or 'n/a'}" for m in matches[:15]
    )
    extra = "" if len(matches) <= 15 else f"\n  ...and {len(matches) - 15} more"
    return (
        f"{query!r} matches multiple companies:\n{listing}{extra}\n"
        "Re-run with a more specific name or the exact ticker."
    )


def lookup_company(conn, query: str) -> CompanyLookupResult:
    """Resolve a free-text name or ticker against DB, then SEC filers.

    Read-only — does not upsert. Used by `resolve`, `analyze`, and `ai-score --company`.
    """
    text = (query or "").strip()
    if not text:
        return CompanyLookupResult(matches=[], used_sec_fallback=False)
    matches = resolve_company(conn, text)
    if matches:
        return CompanyLookupResult(matches=matches, used_sec_fallback=False)
    sec_matches = match_rows(fetch_sec_companies(), text)
    return CompanyLookupResult(matches=sec_matches, used_sec_fallback=bool(sec_matches))


def materialize_company(conn, match: dict, *, upsert: bool = True) -> dict:
    """Enrich a lookup row and optionally persist it to `companies`."""
    company = enrich_companies(conn, [match])[0]
    if upsert:
        repo.upsert_companies(conn, [company])
    return company


def ensure_single_company(conn, query: str, *, upsert: bool = True) -> dict:
    """Return one company row for a unique query; raise if none or many."""
    result = lookup_company(conn, query)
    if not result.matches:
        raise CompanyNotFoundError(query)
    if len(result.matches) > 1:
        raise CompanyAmbiguousError(query, result.matches)
    return materialize_company(conn, result.matches[0], upsert=upsert)


def upsert_tickers_from_sec(conn, tickers: list[str]) -> tuple[list[dict], list[str]]:
    """Upsert missing tickers from SEC `company_tickers.json`.

    Returns ``(upserted_rows, still_missing_tickers)``.
    """
    normalized = [normalize_ticker(t) for t in tickers if str(t).strip()]
    if not normalized:
        return [], []
    existing = {c["ticker"] for c in repo.get_companies(conn, normalized)}
    sec_by_ticker = {r["ticker"]: r for r in fetch_sec_companies()}
    to_upsert: list[dict] = []
    still_missing: list[str] = []
    for ticker in normalized:
        if ticker in existing:
            continue
        row = sec_by_ticker.get(ticker)
        if row is None:
            still_missing.append(ticker)
        else:
            to_upsert.append(dict(row))
    added: list[dict] = []
    if to_upsert:
        added = enrich_companies(conn, apply_domains(to_upsert))
        repo.upsert_companies(conn, added)
    return added, still_missing
