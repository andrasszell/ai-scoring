from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import sqlite3

_PAREN_RE = re.compile(r"\s*\(.*?\)")
_SUFFIX_RE = re.compile(
    r",?\s+(?:Inc\.?|Incorporated|Corporation|Corp\.?|Co\.?|Company|Ltd\.?|LLC|"
    r"L\.?P\.?|plc|Holdings|Group|N\.?V\.?|S\.?A\.?|AG|SE)\b.*$",
    re.IGNORECASE,
)

# Tiny fallback when DB aliases are empty (e.g. before load-companies).
_FALLBACK_QUERY_ALIASES = {
    "GOOGL": "Google",
    "GOOG": "Google",
    "META": "Meta",
    "AMZN": "Amazon.com",
}

# Backward-compatible export for tests/docs referencing QUERY_ALIASES.
QUERY_ALIASES = _FALLBACK_QUERY_ALIASES


def clean_company_name(name: str) -> str:
    """Strip parentheticals and corporate suffixes for cleaner search queries.

    Job boards and the web list employers by brand (e.g. "Apple"), not legal name
    ("Apple Inc."), so the suffix actively hurts matching. Falls back to the
    original name if cleaning would empty it.
    """
    cleaned = _PAREN_RE.sub("", name or "")
    cleaned = _SUFFIX_RE.sub("", cleaned).strip()
    return cleaned or (name or "").strip()


def search_name(company: dict, *, conn: sqlite3.Connection | None = None) -> str:
    """Best query string for a company: DB brand alias, code fallback, else cleaned name."""
    ticker = (company.get("ticker") or "").upper().replace(".", "-")
    if conn is not None:
        from ..db import repository as repo

        aliases = repo.get_aliases(conn, ticker)
        for row in aliases:
            if row.get("alias_type") == "brand" and row.get("alias"):
                return row["alias"]
        for row in aliases:
            if row.get("alias"):
                return row["alias"]
    alias = _FALLBACK_QUERY_ALIASES.get(ticker)
    return alias or clean_company_name(company.get("company_name", ""))


def match_rows(rows: list[dict], query: str) -> list[dict]:
    """Match company rows against a free-text query, narrowest set first.

    Precedence: exact ticker/name, then name prefix, then substring on name or
    ticker. Within a tier, shorter company names rank first.
    """
    ql = query.strip().lower()
    exact = [r for r in rows if r["ticker"].lower() == ql or (r.get("company_name") or "").lower() == ql]
    if exact:
        return exact
    prefix = sorted(
        [r for r in rows if (r.get("company_name") or "").lower().startswith(ql)],
        key=lambda r: len(r.get("company_name") or ""),
    )
    if prefix:
        return prefix
    substring = sorted(
        [r for r in rows if ql in (r.get("company_name") or "").lower() or ql in r["ticker"].lower()],
        key=lambda r: len(r.get("company_name") or ""),
    )
    return substring


def resolve_company(conn, query: str) -> list[dict]:
    """Resolve a free-text company name (or ticker) against the loaded universe."""
    rows = [dict(r) for r in conn.execute("SELECT * FROM companies").fetchall()]
    return match_rows(rows, query)
