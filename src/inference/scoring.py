from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field

# MVP heuristic carried over from the prototype. It derives signal *counts* from
# the evidence corpus (evidence_items) and produces a versioned, explainable score.
#
# Coding Standards compliance:
#  - §5 named formula version (no silent formula changes);
#  - §5 weights are visible named constants, no magic numbers in the function;
#  - §5 returns the numeric score AND an explanation;
#  - §4 score carries score_version, formula_version, input references, explanation.
#
# NOTE (Team 2): there is no `signals` table yet — that abstraction belongs to the
# inference team and would be premature now. As an explicit interim, each collector's
# evidence count acts as one signal, and `input_evidence_ids` records the evidence
# rows that fed the score (a stand-in for `input_signal_ids`).

FORMULA_VERSION = "ai_adoption_score_v0_1"
SCORE_TYPE = "ai_adoption_depth"

WEIGHTS = {
    "sec_filings": 25,
    "earnings_calls": 20,
    "web_products": 25,
    "hiring_jobs": 15,
    "patents": 10,
    "research": 5,
}

CAPS = {
    "sec_filings": 20,
    "earnings_calls": 12,
    "web_products": 8,
    "hiring_jobs": 8,
    "patents": 10,
    "research": 5,
}


@dataclass
class ScoreResult:
    ticker: str
    company_name: str | None
    sector: str | None
    score_value: float
    score_type: str = SCORE_TYPE
    formula_version: str = FORMULA_VERSION
    components: dict[str, float] = field(default_factory=dict)
    explanation: dict = field(default_factory=dict)
    input_evidence_ids: list[int] = field(default_factory=list)

    def to_row(self) -> dict:
        """Flat dict for display/CSV (keeps legacy keys + adds compliance fields)."""
        row = {
            "ticker": self.ticker,
            "company_name": self.company_name,
            "sector": self.sector,
            "score_type": self.score_type,
            "formula_version": self.formula_version,
            "ai_depth_score": self.score_value,
        }
        for name, points in self.components.items():
            row[f"{name}_component"] = points
        row["input_evidence_count"] = len(self.input_evidence_ids)
        return row


def _cap_score(value: float | None, cap: float) -> float:
    if not value or value <= 0:
        return 0.0
    return min(value / cap, 1.0)


def _evidence_counts(conn: sqlite3.Connection, ticker: str) -> dict[str, int]:
    rows = conn.execute(
        "SELECT collector_name, COUNT(*) AS n FROM evidence_items WHERE ticker=? GROUP BY collector_name",
        (ticker,),
    )
    return {r["collector_name"]: r["n"] for r in rows}


def _input_evidence_ids(conn: sqlite3.Connection, ticker: str) -> list[int]:
    rows = conn.execute(
        "SELECT id FROM evidence_items WHERE ticker=? AND collector_name IN (%s) ORDER BY id"
        % ",".join("?" for _ in WEIGHTS),
        [ticker, *WEIGHTS.keys()],
    )
    return [int(r["id"]) for r in rows]


def score_company(conn: sqlite3.Connection, ticker: str, company_name=None, sector=None) -> ScoreResult:
    counts = _evidence_counts(conn, ticker)
    total = 0.0
    components: dict[str, float] = {}
    explanation: dict[str, dict] = {}
    for name, weight in WEIGHTS.items():
        count = counts.get(name, 0)
        ratio = _cap_score(count, CAPS[name])
        points = round(ratio * weight, 2)
        components[name] = points
        explanation[name] = {
            "evidence_count": count,
            "cap": CAPS[name],
            "weight": weight,
            "capped_ratio": round(ratio, 4),
            "points": points,
        }
        total += points
    return ScoreResult(
        ticker=ticker,
        company_name=company_name,
        sector=sector,
        score_value=round(total, 2),
        components=components,
        explanation=explanation,
        input_evidence_ids=_input_evidence_ids(conn, ticker),
    )


def compute_score_results(conn: sqlite3.Connection) -> list[ScoreResult]:
    """Score every company that has at least one collected evidence item."""
    companies = conn.execute(
        """
        SELECT DISTINCT e.ticker AS ticker, c.company_name AS company_name, c.sector AS sector
        FROM evidence_items e
        LEFT JOIN companies c ON c.ticker = e.ticker
        ORDER BY e.ticker
        """
    ).fetchall()
    return [score_company(conn, c["ticker"], c["company_name"], c["sector"]) for c in companies]


def compute_scores(conn: sqlite3.Connection) -> list[dict]:
    """Backwards-compatible flat rows (keeps `ai_depth_score` + `*_component`)."""
    return [r.to_row() for r in compute_score_results(conn)]


def persist_scores(conn: sqlite3.Connection, results: list[ScoreResult]) -> int:
    """Write score rows with version + inputs + explanation (§4). Never overwrites:
    each run appends a new versioned row, preserving history."""
    for r in results:
        conn.execute(
            """
            INSERT INTO scores(ticker, score_type, score_value, score_version,
                               formula_version, input_evidence_ids, explanation_json)
            VALUES(?, ?, ?, ?, ?, ?, ?)
            """,
            (r.ticker, r.score_type, r.score_value, r.formula_version, r.formula_version,
             json.dumps(r.input_evidence_ids), json.dumps(r.explanation)),
        )
    conn.commit()
    return len(results)
