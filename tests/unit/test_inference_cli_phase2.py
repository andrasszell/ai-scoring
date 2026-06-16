import pytest

from evidence_collection.db import repository as repo
from inference.cli import build_parser, cmd_run, cmd_score


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


def _record_status(conn, ticker, collector, source_type, status="success", **kwargs):
    from evidence_collection.models import collector_result
    from evidence_collection.status import CollectionStatus

    run_id = repo.start_run(conn, "collect", {"tickers": [ticker]})
    repo.record_status(
        conn,
        run_id=run_id,
        ticker=ticker,
        source_type=source_type,
        collector_name=collector,
        collector_version="1.0.0",
        result=collector_result(
            CollectionStatus.SUCCESS if status == "success" else status,
            evidence_count=kwargs.get("evidence_count", 1),
            source_hits=kwargs.get("source_hits", 1),
            candidates_after_filter=kwargs.get("candidates_after_filter", 1),
        ),
        duration_seconds=0.1,
    )


ELAN = {
    "ticker": "ELAN",
    "company_name": "Elanco Animal Health Inc",
    "cik": "0001739104",
    "company_id": "ELAN",
}


def test_score_parser_company_flag():
    parser = build_parser()
    args = parser.parse_args(["score", "--company", "Elanco"])
    assert args.company == "Elanco"
    assert args.ticker is None


def test_score_by_company_with_evidence(conn, monkeypatch, capsys):
    monkeypatch.setattr("inference.cli.open_evidence_db", lambda path: conn)
    repo.upsert_companies(conn, [ELAN])
    repo.insert_evidence(conn, _evidence("ELAN", "sec_filings", 3))
    _record_status(conn, "ELAN", "sec_filings", "sec_annual_filing")
    monkeypatch.setattr(
        "inference.cli.resolve_for_scoring",
        lambda c, q: ELAN,
    )
    cmd_score(type("A", (), {"db": "unused", "company": "Elanco", "ticker": None, "persist": False})())
    out = capsys.readouterr().out
    assert "ELAN" in out
    assert "/ 100" in out


def test_score_by_company_without_evidence_exits(conn, monkeypatch):
    monkeypatch.setattr("inference.cli.open_evidence_db", lambda path: conn)
    monkeypatch.setattr(
        "inference.cli.resolve_for_scoring",
        lambda c, q: ELAN,
    )
    with pytest.raises(SystemExit, match="No evidence"):
        cmd_score(type("A", (), {"db": "unused", "company": "Elanco", "ticker": None, "persist": False})())


def test_run_collects_when_no_evidence(conn, monkeypatch, capsys):
    monkeypatch.setattr("inference.cli.open_evidence_db", lambda path: conn)
    repo.upsert_companies(conn, [ELAN])
    collected = {"called": False}

    def fake_run(*args, **kwargs):
        collected["called"] = True
        repo.insert_evidence(conn, _evidence("ELAN", "sec_filings", 2))
        _record_status(conn, "ELAN", "sec_filings", "sec_annual_filing")
        return {
            "run_id": 1,
            "evidence": 2,
            "documents": 0,
            "ok": 1,
            "failed": 0,
            "runtime_seconds": 0.1,
        }

    monkeypatch.setattr("inference.cli.resolve_for_scoring", lambda c, q: ELAN)
    monkeypatch.setattr("inference.cli.run_collection", fake_run)
    monkeypatch.setattr("inference.cli.get_collectors", lambda s: [])
    cmd_run(
        type(
            "A",
            (),
            {
                "db": "unused",
                "company": "Elanco",
                "collect": False,
                "source": None,
                "persist": False,
            },
        )()
    )
    assert collected["called"]
    assert "ELAN" in capsys.readouterr().out
