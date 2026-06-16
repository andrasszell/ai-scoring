from evidence_collection.db import repository as repo
from inference.scoring import (
    FORMULA_VERSION,
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


def test_only_companies_with_evidence_are_scored(conn):
    repo.upsert_companies(conn, [
        {"ticker": "MSFT", "company_name": "Microsoft Corporation"},
        {"ticker": "AAPL", "company_name": "Apple Inc."},
    ])
    # Only MSFT has evidence.
    repo.insert_evidence(conn, _evidence("MSFT", "sec_filings", 5))
    scores = compute_scores(conn)
    assert [s["ticker"] for s in scores] == ["MSFT"]


def test_score_caps_and_weights(conn):
    repo.upsert_companies(conn, [{"ticker": "MSFT", "company_name": "Microsoft Corporation"}])
    # sec_filings cap is 20, weight 25 -> 5 items = 5/20 * 25 = 6.25
    repo.insert_evidence(conn, _evidence("MSFT", "sec_filings", 5))
    score = compute_scores(conn)[0]
    assert score["sec_filings_component"] == 6.25
    assert score["ai_depth_score"] == 6.25


def test_score_is_capped_at_weight(conn):
    repo.upsert_companies(conn, [{"ticker": "MSFT", "company_name": "Microsoft Corporation"}])
    # 100 web_products items exceed the cap (8); component should max at weight (25).
    repo.insert_evidence(conn, _evidence("MSFT", "web_products", 100))
    score = compute_scores(conn)[0]
    assert score["web_products_component"] == 25.0


def test_score_result_carries_version_and_explanation(conn):
    repo.upsert_companies(conn, [{"ticker": "MSFT", "company_name": "Microsoft Corporation"}])
    repo.insert_evidence(conn, _evidence("MSFT", "sec_filings", 5))
    result = score_company(conn, "MSFT", "Microsoft Corporation", "Tech")
    # §5: named formula version.
    assert result.formula_version == FORMULA_VERSION
    # §5: explanation present per driver.
    assert result.explanation["sec_filings"]["evidence_count"] == 5
    assert result.explanation["sec_filings"]["points"] == 6.25
    # §4: input references recorded (interim stand-in for input_signal_ids).
    assert len(result.input_evidence_ids) == 5


def test_persist_scores_records_versioned_rows(conn):
    repo.upsert_companies(conn, [{"ticker": "MSFT", "company_name": "Microsoft Corporation"}])
    repo.insert_evidence(conn, _evidence("MSFT", "sec_filings", 5))
    n = persist_scores(conn, compute_score_results(conn))
    assert n == 1
    row = conn.execute("SELECT * FROM scores WHERE ticker='MSFT'").fetchone()
    assert row["formula_version"] == FORMULA_VERSION
    assert row["score_value"] == 6.25
    assert row["explanation_json"]
    assert row["input_evidence_ids"]


def test_missing_signals_do_not_crash_and_score_zero_components(conn):
    repo.upsert_companies(conn, [{"ticker": "MSFT", "company_name": "Microsoft Corporation"}])
    # Only one source present; all others must be 0 without error.
    repo.insert_evidence(conn, _evidence("MSFT", "sec_filings", 3))
    result = score_company(conn, "MSFT", "Microsoft Corporation", None)
    assert result.components["patents"] == 0.0
    assert result.components["research"] == 0.0
    assert result.score_value > 0
