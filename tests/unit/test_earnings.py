import json
from datetime import date

import pytest

from evidence_collection.collectors.earnings import EarningsCallCollector
from evidence_collection.config import settings
from evidence_collection.dates import DATE_PROVENANCE_ORIGIN, DATE_PROVENANCE_QUARTER_ANCHOR
from evidence_collection.db import repository as repo
from evidence_collection.models import CollectionContext
from evidence_collection.outcomes import OutcomeReason
from evidence_collection.status import CollectionStatus

COMPANY = {"ticker": "MSFT", "company_name": "Microsoft Corporation", "company_id": "MSFT"}


@pytest.fixture(autouse=True)
def _seed_company(conn):
    repo.upsert_companies(conn, [COMPANY])

AI_TRANSCRIPT = (
    "We continue to invest in artificial intelligence and machine learning capabilities "
    "across Azure, Copilot, and our enterprise product portfolio for customers worldwide."
)


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def _earnings_settings(tmp_path):
    return type(
        "Settings",
        (),
        {
            "fmp_api_key": "test-fmp-key",
            "raw_dir": str(tmp_path),
            "max_candidate_paragraphs": 40,
        },
    )()


def test_earnings_api_key_missing(conn, monkeypatch):
    monkeypatch.setattr(
        "evidence_collection.collectors.earnings.settings",
        type("S", (), {"fmp_api_key": ""})(),
    )
    ctx = CollectionContext(conn=conn, run_id=1, settings=settings)
    result = EarningsCallCollector().collect(ctx, COMPANY)
    assert result.status == CollectionStatus.API_KEY_MISSING


def test_earnings_no_results_when_fmp_returns_empty(conn, monkeypatch, tmp_path):
    monkeypatch.setattr(
        "evidence_collection.collectors.earnings.settings",
        _earnings_settings(tmp_path),
    )

    def fake_get(url, params=None):
        return _FakeResponse([])

    monkeypatch.setattr("evidence_collection.collectors.earnings.get", fake_get)
    ctx = CollectionContext(conn=conn, run_id=1, settings=settings)
    result = EarningsCallCollector().collect(ctx, COMPANY, limit_quarters=1)
    assert result.status == CollectionStatus.NO_RESULTS
    assert result.outcome_reason == OutcomeReason.SOURCE_EMPTY
    assert result.evidence_count == 0


def test_earnings_skips_empty_transcript_content(conn, monkeypatch, tmp_path):
    monkeypatch.setattr(
        "evidence_collection.collectors.earnings.settings",
        _earnings_settings(tmp_path),
    )
    current_year = date.today().year

    def fake_get(url, params=None):
        if params["year"] == current_year and params["quarter"] == 4:
            return _FakeResponse([{"date": "2025-10-25", "content": "   "}])
        return _FakeResponse([])

    monkeypatch.setattr("evidence_collection.collectors.earnings.get", fake_get)
    ctx = CollectionContext(conn=conn, run_id=1, settings=settings)
    result = EarningsCallCollector().collect(ctx, COMPANY, limit_quarters=1)
    assert result.status == CollectionStatus.NO_RESULTS
    assert result.outcome_reason == OutcomeReason.SOURCE_EMPTY


def test_earnings_continues_after_fetch_error(conn, monkeypatch, tmp_path):
    monkeypatch.setattr(
        "evidence_collection.collectors.earnings.settings",
        _earnings_settings(tmp_path),
    )
    current_year = date.today().year
    calls = {"n": 0}

    def fake_get(url, params=None):
        calls["n"] += 1
        if params["year"] == current_year and params["quarter"] == 4:
            raise RuntimeError("network blip")
        if params["year"] == current_year and params["quarter"] == 3:
            return _FakeResponse(
                [{"date": "2025-07-18", "content": AI_TRANSCRIPT}],
            )
        return _FakeResponse([])

    monkeypatch.setattr("evidence_collection.collectors.earnings.get", fake_get)
    ctx = CollectionContext(conn=conn, run_id=1, settings=settings)
    result = EarningsCallCollector().collect(ctx, COMPANY, limit_quarters=1)
    assert result.status == CollectionStatus.SUCCESS
    assert result.evidence_count >= 1
    assert result.documents_count == 1
    assert calls["n"] >= 2


def test_earnings_stores_source_date_and_date_provenance(conn, monkeypatch, tmp_path):
    monkeypatch.setattr(
        "evidence_collection.collectors.earnings.settings",
        _earnings_settings(tmp_path),
    )
    current_year = date.today().year

    def fake_get(url, params=None):
        if params["year"] == current_year and params["quarter"] == 4:
            return _FakeResponse([{"content": AI_TRANSCRIPT}])
        return _FakeResponse([])

    monkeypatch.setattr("evidence_collection.collectors.earnings.get", fake_get)
    ctx = CollectionContext(conn=conn, run_id=1, settings=settings)
    result = EarningsCallCollector().collect(ctx, COMPANY, limit_quarters=1)
    assert result.status == CollectionStatus.SUCCESS

    row = conn.execute(
        "SELECT source_date, metadata_json FROM evidence_items WHERE ticker='MSFT' AND collector_name='earnings_calls'"
    ).fetchone()
    assert row["source_date"] == f"{current_year}-12-01"
    meta = json.loads(row["metadata_json"])
    assert meta["date_provenance"] == DATE_PROVENANCE_QUARTER_ANCHOR

    doc = conn.execute(
        "SELECT source_date, metadata_json, text_path FROM documents WHERE ticker='MSFT' AND source_type='earnings_call_transcript'"
    ).fetchone()
    assert doc["source_date"] == f"{current_year}-12-01"
    doc_meta = json.loads(doc["metadata_json"])
    assert doc_meta["date_provenance"] == DATE_PROVENANCE_QUARTER_ANCHOR
    assert doc["text_path"]


def test_earnings_uses_fmp_date_provenance_when_present(conn, monkeypatch, tmp_path):
    monkeypatch.setattr(
        "evidence_collection.collectors.earnings.settings",
        _earnings_settings(tmp_path),
    )
    current_year = date.today().year

    def fake_get(url, params=None):
        if params["year"] == current_year and params["quarter"] == 2:
            return _FakeResponse([{"date": "2025-04-28", "content": AI_TRANSCRIPT}])
        return _FakeResponse([])

    monkeypatch.setattr("evidence_collection.collectors.earnings.get", fake_get)
    ctx = CollectionContext(conn=conn, run_id=1, settings=settings)
    EarningsCallCollector().collect(ctx, COMPANY, limit_quarters=1)

    row = conn.execute(
        "SELECT source_date, metadata_json FROM evidence_items WHERE ticker='MSFT' AND collector_name='earnings_calls'"
    ).fetchone()
    assert row["source_date"] == "2025-04-28"
    meta = json.loads(row["metadata_json"])
    assert meta["date_provenance"] == DATE_PROVENANCE_ORIGIN
