"""Tiny end-to-end fixture (Coding Standards §8):

    raw evidence -> candidate evidence -> stored evidence -> score -> explanation

This guards the whole pipeline against AI-generated drift. If extraction, the
evidence schema, or the scorer change in a way that breaks the chain, this fails.
"""
from pathlib import Path

from evidence_collection.collectors.base import Collector
from evidence_collection.db import repository as repo
from evidence_collection.extraction import candidate_paragraphs
from evidence_collection.sources import Reliability, SourceCategory
from inference.scoring import compute_scores

FIXTURE = Path(__file__).parent.parent / "fixtures" / "sample_filing.txt"


class _FixtureSecCollector(Collector):
    name = "sec_filings"
    version = "1.0.0"
    source_type = "sec_annual_filing"

    def collect(self, ctx, company):  # pragma: no cover - we only use make_evidence
        raise NotImplementedError


def test_raw_to_score_with_explanation(conn):
    company = {"ticker": "TEST", "company_name": "Test Industrials Inc."}
    repo.upsert_companies(conn, [company])

    # 1. raw evidence -> candidate evidence (only AI paragraphs survive)
    raw = FIXTURE.read_text()
    candidates = candidate_paragraphs(raw)
    assert len(candidates) >= 2  # the AI/ML and computer-vision paragraphs
    # The "installments" paragraph must NOT be flagged (whole-word matching).
    assert not any("installment" in c["text"].lower() for c in candidates)

    # 2. candidate evidence -> stored evidence items (traceability fields present)
    collector = _FixtureSecCollector()
    rows = [collector.make_evidence(company, evidence_text=c["text"], source_url="http://sec/x",
                                    source_date="2026-01-01", metadata={"keywords": c["keywords"]})
            for c in candidates]
    repo.insert_evidence(conn, rows)

    stored = conn.execute("SELECT * FROM evidence_items WHERE ticker='TEST'").fetchall()
    assert stored, "evidence must be persisted"
    first = dict(stored[0])
    # §1/§4: every evidence item is source-linked and hashed.
    assert first["source_url"] == "http://sec/x"
    assert first["raw_hash"]
    assert first["collector_name"] == "sec_filings"
    assert first["collector_version"] == "1.0.0"
    # §6: classified source category + reliability + initial confidence.
    assert first["source_category"] == SourceCategory.REGULATORY_FILING
    assert first["source_reliability"] == Reliability.HIGH
    assert first["confidence_initial"] == 0.75

    # 3. score -> explanation (per-component breakdown is the explanation)
    scores = compute_scores(conn)
    assert [s["ticker"] for s in scores] == ["TEST"]
    score = scores[0]
    assert score["ai_depth_score"] > 0
    assert "sec_filings_component" in score  # explainable driver
    assert score["sec_filings_component"] > 0
