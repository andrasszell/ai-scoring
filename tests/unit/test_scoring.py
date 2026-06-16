from evidence_collection.db import repository as repo
from evidence_collection.models import CollectorResult, collector_result
from evidence_collection.outcomes import OutcomeReason
from evidence_collection.status import CollectionStatus
from inference.scoring import (
    CAPS,
    FORMULA_VERSION,
    WEIGHTS,
    compute_score_results,
    compute_scores,
    persist_scores,
    score_company,
)


def _evidence(ticker, collector, n):
    return [
        {
            "ticker": ticker,
            "company_name": f"{ticker} Inc.",
            "source_type": "x",
            "evidence_text": f"machine learning {i}",
            "collector_name": collector,
            "collector_version": "1.0.0",
            "source_url": f"http://src/{ticker}/{collector}/{i}",
            "raw_hash": f"{ticker}-{collector}-{i}",
        }
        for i in range(n)
    ]


def _record_status(conn, ticker, collector, source_type, result):
    run_id = repo.start_run(conn, "collect", {"tickers": [ticker]})
    repo.record_status(
        conn,
        run_id=run_id,
        ticker=ticker,
        source_type=source_type,
        collector_name=collector,
        collector_version="1.0.0",
        result=result,
        duration_seconds=0.1,
    )


def test_weights_and_caps_cover_all_pillars():
    assert set(WEIGHTS) == set(CAPS)
    assert sum(WEIGHTS.values()) == 100


def test_only_companies_with_evidence_are_scored(conn):
    repo.upsert_companies(conn, [
        {"ticker": "MSFT", "company_name": "Microsoft Corporation"},
        {"ticker": "AAPL", "company_name": "Apple Inc."},
    ])
    repo.insert_evidence(conn, _evidence("MSFT", "sec_filings", 5))
    scores = compute_scores(conn)
    assert [s["ticker"] for s in scores] == ["MSFT"]


def test_score_caps_and_weights(conn):
    repo.upsert_companies(conn, [{"ticker": "MSFT", "company_name": "Microsoft Corporation"}])
    repo.insert_evidence(conn, _evidence("MSFT", "sec_filings", 5))
    _record_status(
        conn,
        "MSFT",
        "sec_filings",
        "sec_annual_filing",
        collector_result(CollectionStatus.SUCCESS, evidence_count=5, source_hits=1, candidates_after_filter=5),
    )
    score = compute_scores(conn)[0]
    assert score["sec_filings_component"] == 25.0
    assert score["ai_depth_score"] == 25.0


def test_score_is_capped_at_redistributed_weight(conn):
    repo.upsert_companies(conn, [{"ticker": "MSFT", "company_name": "Microsoft Corporation"}])
    repo.insert_evidence(conn, _evidence("MSFT", "web_products", 100))
    _record_status(
        conn,
        "MSFT",
        "web_products",
        "web_search_product",
        collector_result(CollectionStatus.SUCCESS, evidence_count=100, source_hits=100, candidates_after_filter=100),
    )
    score = compute_scores(conn)[0]
    assert score["web_products_component"] == 100.0


def test_score_result_carries_version_and_explanation(conn):
    repo.upsert_companies(conn, [{"ticker": "MSFT", "company_name": "Microsoft Corporation"}])
    repo.insert_evidence(conn, _evidence("MSFT", "sec_filings", 5))
    _record_status(
        conn,
        "MSFT",
        "sec_filings",
        "sec_annual_filing",
        collector_result(CollectionStatus.SUCCESS, evidence_count=5, source_hits=1, candidates_after_filter=5),
    )
    result = score_company(conn, "MSFT", "Microsoft Corporation", "Tech")
    assert result.formula_version == FORMULA_VERSION
    assert result.explanation["sec_filings"]["evidence_count"] == 5
    assert result.explanation["sec_filings"]["points"] == 25.0
    assert len(result.input_evidence_ids) == 5


def test_persist_scores_records_versioned_rows(conn):
    repo.upsert_companies(conn, [{"ticker": "MSFT", "company_name": "Microsoft Corporation"}])
    repo.insert_evidence(conn, _evidence("MSFT", "sec_filings", 5))
    _record_status(
        conn,
        "MSFT",
        "sec_filings",
        "sec_annual_filing",
        collector_result(CollectionStatus.SUCCESS, evidence_count=5, source_hits=1, candidates_after_filter=5),
    )
    n = persist_scores(conn, compute_score_results(conn))
    assert n == 1
    row = conn.execute("SELECT * FROM scores WHERE ticker='MSFT'").fetchone()
    assert row["formula_version"] == FORMULA_VERSION
    assert row["score_value"] == 25.0
    assert row["explanation_json"]
    assert row["input_evidence_ids"]


def test_unmeasured_pillars_excluded_and_weights_redistributed(conn):
    repo.upsert_companies(conn, [{"ticker": "MSFT", "company_name": "Microsoft Corporation"}])
    repo.insert_evidence(conn, _evidence("MSFT", "sec_filings", 3))
    _record_status(
        conn,
        "MSFT",
        "sec_filings",
        "sec_annual_filing",
        collector_result(CollectionStatus.SUCCESS, evidence_count=3, source_hits=1, candidates_after_filter=3),
    )
    _record_status(
        conn,
        "MSFT",
        "patents",
        "patent",
        CollectorResult(CollectionStatus.API_KEY_MISSING, message="missing key"),
    )
    result = score_company(conn, "MSFT", "Microsoft Corporation", None)
    assert result.explanation["patents"]["excluded"] is True
    assert result.components["patents"] == 0.0
    assert result.components["sec_filings"] == 15.0
    assert result.score_value == 15.0


def test_failed_pillar_excluded_not_scored_as_zero_evidence(conn):
    repo.upsert_companies(conn, [{"ticker": "MSFT", "company_name": "Microsoft Corporation"}])
    _record_status(
        conn,
        "MSFT",
        "research",
        "research_paper",
        CollectorResult(CollectionStatus.SOURCE_UNAVAILABLE, message="timeout"),
    )
    result = score_company(conn, "MSFT", "Microsoft Corporation", None)
    assert result.explanation["research"]["excluded"] is True
    assert "research" in result.explanation["_meta"]["excluded_pillars"]


def test_filtered_to_zero_flagged_low_confidence(conn):
    repo.upsert_companies(conn, [{"ticker": "MSFT", "company_name": "Microsoft Corporation"}])
    _record_status(
        conn,
        "MSFT",
        "sec_filings",
        "sec_annual_filing",
        collector_result(
            CollectionStatus.NO_RESULTS,
            outcome_reason=OutcomeReason.FILTERED_TO_ZERO,
            message="filing stored; no AI paragraphs",
            documents_count=1,
            source_hits=1,
        ),
    )
    result = score_company(conn, "MSFT", "Microsoft Corporation", None)
    assert result.explanation["sec_filings"]["low_confidence"] is True
    assert result.explanation["sec_filings"]["outcome_reason"] == OutcomeReason.FILTERED_TO_ZERO
    assert result.components["sec_filings"] == 0.0


def test_input_evidence_ids_exclude_unmeasured_pillars(conn):
    repo.upsert_companies(conn, [{"ticker": "MSFT", "company_name": "Microsoft Corporation"}])
    repo.insert_evidence(conn, _evidence("MSFT", "sec_filings", 3))
    repo.insert_evidence(conn, _evidence("MSFT", "research", 2))
    _record_status(
        conn,
        "MSFT",
        "sec_filings",
        "sec_annual_filing",
        collector_result(CollectionStatus.SUCCESS, evidence_count=3, source_hits=1, candidates_after_filter=3),
    )
    _record_status(
        conn,
        "MSFT",
        "research",
        "research_paper",
        CollectorResult(CollectionStatus.SOURCE_UNAVAILABLE, message="timeout"),
    )
    result = score_company(conn, "MSFT", "Microsoft Corporation", None)
    assert result.explanation["research"]["excluded"] is True
    assert len(result.input_evidence_ids) == 3
    ids_for_research = conn.execute(
        "SELECT id FROM evidence_items WHERE ticker='MSFT' AND collector_name='research'"
    ).fetchall()
    assert ids_for_research
    assert all(int(r["id"]) not in result.input_evidence_ids for r in ids_for_research)


def test_v0_2_redistributes_when_pillars_excluded(conn):
    """Regression: excluded pillars must not shrink the score denominator."""
    repo.upsert_companies(conn, [{"ticker": "MSFT", "company_name": "Microsoft Corporation"}])
    repo.insert_evidence(conn, _evidence("MSFT", "sec_filings", 5))
    _record_status(
        conn,
        "MSFT",
        "sec_filings",
        "sec_annual_filing",
        collector_result(CollectionStatus.SUCCESS, evidence_count=5, source_hits=1, candidates_after_filter=5),
    )
    _record_status(
        conn,
        "MSFT",
        "patents",
        "patent",
        CollectorResult(CollectionStatus.API_KEY_MISSING, message="missing key"),
    )
    _record_status(
        conn,
        "MSFT",
        "earnings_calls",
        "earnings_call_transcript",
        CollectorResult(CollectionStatus.API_KEY_MISSING, message="missing key"),
    )
    result = score_company(conn, "MSFT", "Microsoft Corporation", None)
    # Only sec measured: 5/20 * 100 = 25.0 (not 5/20 * 25 = 6.25 under v0_1).
    assert result.components["sec_filings"] == 25.0
    assert result.score_value == 25.0
