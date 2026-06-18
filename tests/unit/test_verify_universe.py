from evidence_collection.universe.verify import DEFAULT_SPOT_CHECK, spot_check_tickers, universe_stats


def test_universe_stats_on_loaded_db(conn):
    from evidence_collection.db import repository as repo

    repo.upsert_companies(
        conn,
        [{"ticker": "MSFT", "company_name": "Microsoft", "cik": "0000789019"}],
    )
    stats = universe_stats(conn)
    assert stats["total_companies"] >= 1
    assert stats["pilot_ticker_count"] == 50
    assert stats["pilot_with_domain_config"] == 50


def test_spot_check_tickers(conn):
    rows = spot_check_tickers(conn, DEFAULT_SPOT_CHECK[:3])
    assert len(rows) == 3
    assert all("ticker" in row for row in rows)
