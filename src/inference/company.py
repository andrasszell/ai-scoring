from __future__ import annotations

import sqlite3

from evidence_collection.db import apply_migrations, connect
from evidence_collection.universe.lookup import (
    CompanyAmbiguousError,
    CompanyNotFoundError,
    ensure_single_company,
)

from .scoring import ScoreResult, score_company


def open_evidence_db(db_path: str) -> sqlite3.Connection:
    """Open the shared evidence database with migrations applied."""
    conn = connect(db_path)
    apply_migrations(conn)
    return conn


def evidence_count(conn: sqlite3.Connection, ticker: str) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM evidence_items WHERE ticker=?",
        (ticker.upper().replace(".", "-"),),
    ).fetchone()
    return int(row["n"])


def resolve_for_scoring(conn: sqlite3.Connection, query: str) -> dict:
    """Resolve and upsert a company for scoring commands."""
    return ensure_single_company(conn, query, upsert=True)


def score_resolved_company(conn: sqlite3.Connection, company: dict) -> ScoreResult:
    """Score one company; fail clearly when no evidence exists."""
    ticker = company["ticker"]
    if evidence_count(conn, ticker) == 0:
        raise ValueError(
            f"No evidence for {ticker}. Collect first: "
            f"ai-collect analyze {query_hint(company)!r} "
            f"or ai-score run --company {query_hint(company)!r}"
        )
    return score_company(
        conn,
        ticker,
        company.get("company_name"),
        company.get("sector"),
    )


def query_hint(company: dict) -> str:
    return company.get("company_name") or company["ticker"]


def print_score_result(result: ScoreResult) -> None:
    """Human-readable score + explanation (Coding Standards §5)."""
    print(
        f"\n{result.ticker} — {result.company_name}: {result.score_value} / 100  "
        f"[{result.score_type} {result.formula_version}]"
    )
    meta = result.explanation.get("_meta") or {}
    excluded = meta.get("excluded_pillars") or []
    if excluded:
        print(f"    excluded pillars: {', '.join(excluded)}")
    for name, exp in result.explanation.items():
        if name.startswith("_"):
            continue
        if exp.get("excluded"):
            reason = exp.get("reason") or exp.get("status") or "excluded"
            print(f"    {'—':>6}  {name:<14} excluded ({reason})")
            continue
        suffix = " [low confidence]" if exp.get("low_confidence") else ""
        print(
            f"    {exp['points']:>6}  {name:<14} "
            f"(count={exp['evidence_count']}, cap={exp.get('cap')}, "
            f"weight={exp.get('weight')}){suffix}"
        )
    print(f"    inputs: {len(result.input_evidence_ids)} evidence items")


__all__ = [
    "CompanyAmbiguousError",
    "CompanyNotFoundError",
    "evidence_count",
    "open_evidence_db",
    "print_score_result",
    "query_hint",
    "resolve_for_scoring",
    "score_resolved_company",
]
