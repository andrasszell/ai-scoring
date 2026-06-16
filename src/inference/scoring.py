from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field

from evidence_collection.db import repository as repo
from evidence_collection.outcomes import OutcomeReason, parse_outcome_reason
from evidence_collection.status import CollectionStatus

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

FORMULA_VERSION = "ai_adoption_score_v0_2"
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

EXCLUDE_PILLAR_STATUSES = frozenset(
    {
        CollectionStatus.API_KEY_MISSING,
        CollectionStatus.SKIPPED,
        CollectionStatus.SOURCE_UNAVAILABLE,
        CollectionStatus.RATE_LIMITED,
        CollectionStatus.PARSE_FAILED,
        CollectionStatus.API_LIMIT_REACHED,
        CollectionStatus.COMPANY_NOT_FOUND,
        CollectionStatus.AMBIGUOUS_COMPANY,
    }
)


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


def _input_evidence_ids(
    conn: sqlite3.Connection, ticker: str, measured_collectors: frozenset[str] | None = None
) -> list[int]:
    collectors = measured_collectors if measured_collectors is not None else frozenset(WEIGHTS)
    if not collectors:
        return []
    rows = conn.execute(
        "SELECT id FROM evidence_items WHERE ticker=? AND collector_name IN (%s) ORDER BY id"
        % ",".join("?" for _ in collectors),
        [ticker, *sorted(collectors)],
    )
    return [int(r["id"]) for r in rows]


def _latest_status_by_collector(conn: sqlite3.Connection, ticker: str) -> dict[str, dict]:
    return {r["collector_name"]: r for r in repo.status_summary(conn, [ticker])}


def _pillar_measured(status_row: dict | None, evidence_count: int) -> tuple[bool, str | None]:
    """Return whether a pillar was measured and an exclusion reason when not."""
    if status_row is None:
        if evidence_count > 0:
            return True, None
        return False, "never_collected"
    status = status_row["status"]
    if status in EXCLUDE_PILLAR_STATUSES:
        return False, status
    if status in (CollectionStatus.SUCCESS, CollectionStatus.NO_RESULTS):
        return True, None
    return False, status


def score_company(conn: sqlite3.Connection, ticker: str, company_name=None, sector=None) -> ScoreResult:
    counts = _evidence_counts(conn, ticker)
    statuses = _latest_status_by_collector(conn, ticker)
    measured: dict[str, float] = {}
    explanation: dict[str, dict] = {}

    for name, weight in WEIGHTS.items():
        count = counts.get(name, 0)
        status_row = statuses.get(name)
        is_measured, exclusion = _pillar_measured(status_row, count)
        outcome_reason = (
            parse_outcome_reason(status_row.get("message")) if status_row else None
        )
        if not is_measured:
            explanation[name] = {
                "excluded": True,
                "status": status_row["status"] if status_row else None,
                "reason": exclusion,
                "evidence_count": count,
                "weight": weight,
                "points": 0.0,
            }
            continue
        measured[name] = weight
        low_confidence = outcome_reason == OutcomeReason.FILTERED_TO_ZERO
        explanation[name] = {
            "excluded": False,
            "evidence_count": count,
            "cap": CAPS[name],
            "weight": weight,
            "status": status_row["status"] if status_row else None,
            "outcome_reason": outcome_reason,
            "low_confidence": low_confidence,
        }

    measured_weight_total = sum(measured.values()) or 1.0
    total = 0.0
    components: dict[str, float] = {}
    for name, weight in WEIGHTS.items():
        if name not in measured:
            components[name] = 0.0
            continue
        count = counts.get(name, 0)
        effective_weight = weight * (100.0 / measured_weight_total)
        ratio = _cap_score(count, CAPS[name])
        points = round(ratio * effective_weight, 2)
        components[name] = points
        explanation[name]["effective_weight"] = round(effective_weight, 2)
        explanation[name]["capped_ratio"] = round(ratio, 4)
        explanation[name]["points"] = points
        total += points

    explanation["_meta"] = {
        "measured_pillars": sorted(measured.keys()),
        "excluded_pillars": sorted(n for n in WEIGHTS if n not in measured),
        "measured_weight_total": measured_weight_total,
        "input_evidence_collectors": sorted(measured.keys()),
    }
    measured_names = frozenset(measured.keys())
    return ScoreResult(
        ticker=ticker,
        company_name=company_name,
        sector=sector,
        score_value=round(total, 2),
        components=components,
        explanation=explanation,
        input_evidence_ids=_input_evidence_ids(conn, ticker, measured_names),
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
