from __future__ import annotations

import re

_PAREN_RE = re.compile(r"\s*\(.*?\)")
_SUFFIX_RE = re.compile(
    r",?\s+(?:Inc\.?|Incorporated|Corporation|Corp\.?|Co\.?|Company|Ltd\.?|LLC|"
    r"L\.?P\.?|plc|Holdings|Group|N\.?V\.?|S\.?A\.?|AG|SE)\b.*$",
    re.IGNORECASE,
)

# Employer brand names used by job boards / search differ from legal/index names.
# Keyed by ticker for precision. Extend as needed.
QUERY_ALIASES = {
    "GOOGL": "Google",
    "GOOG": "Google",
    "META": "Meta",
    "AMZN": "Amazon.com",
}


def clean_company_name(name: str) -> str:
    """Strip parentheticals and corporate suffixes for cleaner search queries.

    Job boards and the web list employers by brand (e.g. "Apple"), not legal name
    ("Apple Inc."), so the suffix actively hurts matching. Falls back to the
    original name if cleaning would empty it.
    """
    cleaned = _PAREN_RE.sub("", name or "")
    cleaned = _SUFFIX_RE.sub("", cleaned).strip()
    return cleaned or (name or "").strip()


def search_name(company: dict) -> str:
    """Best query string for a company: a known brand alias, else its cleaned name."""
    alias = QUERY_ALIASES.get((company.get("ticker") or "").upper())
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
