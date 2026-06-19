import json

import pandas as pd

from evidence_collection.db import repository as repo
from evidence_collection.exporters import export_evidence_jsonl, export_table_csv, export_table_parquet


def _seed(conn):
    repo.upsert_companies(conn, [
        {"ticker": "MSFT", "company_name": "Microsoft Corporation"},
        {"ticker": "AAPL", "company_name": "Apple Inc."},
    ])
    repo.insert_evidence(conn, [
        {"ticker": "MSFT", "company_name": "Microsoft Corporation", "source_type": "x",
         "evidence_text": "ml", "collector_name": "sec_filings", "collector_version": "1.0.0",
         "source_url": "http://src/msft", "raw_hash": "h-msft",
         "metadata_json": json.dumps({"k": 1})},
        {"ticker": "AAPL", "company_name": "Apple Inc.", "source_type": "x",
         "evidence_text": "ai", "collector_name": "sec_filings", "collector_version": "1.0.0",
         "source_url": "http://src/aapl", "raw_hash": "h-aapl"},
    ])


def test_export_csv_respects_ticker_filter(conn, tmp_path):
    _seed(conn)
    out = tmp_path / "evidence.csv"
    n = export_table_csv(conn, "evidence_items", out, ["MSFT"])
    assert n == 1
    assert "MSFT" in out.read_text()
    assert "AAPL" not in out.read_text()


def test_export_jsonl_parses_metadata(conn, tmp_path):
    _seed(conn)
    out = tmp_path / "evidence.jsonl"
    n = export_evidence_jsonl(conn, out, ["MSFT"])
    assert n == 1
    record = json.loads(out.read_text().splitlines()[0])
    assert record["ticker"] == "MSFT"
    assert record["metadata"] == {"k": 1}


def test_export_parquet_respects_ticker_filter(conn, tmp_path):
    _seed(conn)
    out = tmp_path / "evidence.parquet"
    n = export_table_parquet(conn, "evidence_items", out, ["MSFT"])
    assert n == 1
    df = pd.read_parquet(out)
    assert list(df["ticker"]) == ["MSFT"]


def test_export_empty_table_writes_header_only(conn, tmp_path):
    out = tmp_path / "companies.csv"
    n = export_table_csv(conn, "companies", out)
    assert n == 0
    assert out.read_text().strip() != ""
