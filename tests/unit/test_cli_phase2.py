import pytest

from evidence_collection.cli import build_parser, cmd_collect, cmd_resolve
from evidence_collection.db import repository as repo


ELAN_SEC = {
    "ticker": "ELAN",
    "company_name": "Elanco Animal Health Inc",
    "cik": "0001739104",
    "sector": None,
    "industry": None,
    "exchange": None,
    "country": "US",
    "source_of_identifier": "sec_company_tickers",
}


@pytest.fixture
def patch_cli_db(conn, tmp_path, monkeypatch):
    """Point ai-collect CLI at the pytest SQLite file."""
    db_path = tmp_path / "test.sqlite"
    monkeypatch.setattr(
        "evidence_collection.cli.settings",
        type("S", (), {"db_path": db_path, "log_level": "WARNING"})(),
    )
    return conn


def test_resolve_parser_exists():
    parser = build_parser()
    args = parser.parse_args(["resolve", "ELAN"])
    assert args.command == "resolve"
    assert args.name == ["ELAN"]


def test_cmd_resolve_sec_filer(monkeypatch, patch_cli_db, capsys):
    monkeypatch.setattr(
        "evidence_collection.cli.lookup_company",
        lambda c, q: type("R", (), {"matches": [ELAN_SEC], "used_sec_fallback": True})(),
    )
    cmd_resolve(type("A", (), {"name": ["ELAN"]})())
    out = capsys.readouterr().out
    assert "ELAN" in out
    assert "0001739104" in out
    assert "SEC filers" in out


def test_cmd_resolve_ambiguous_exits(patch_cli_db):
    repo.upsert_companies(patch_cli_db, [
        {"ticker": "ABC", "company_name": "Alpha Beta Corp"},
        {"ticker": "ABD", "company_name": "Alpha Beta Devices"},
    ])
    with pytest.raises(SystemExit, match="matches multiple"):
        cmd_resolve(type("A", (), {"name": ["Alpha Beta"]})())


def test_collect_upserts_missing_ticker_from_sec(monkeypatch, patch_cli_db):
    monkeypatch.setattr(
        "evidence_collection.universe.lookup.fetch_sec_companies",
        lambda: [ELAN_SEC],
    )
    monkeypatch.setattr(
        "evidence_collection.cli.run_collection",
        lambda *a, **k: {"run_id": 1, "evidence": 0, "documents": 0, "ok": 0, "failed": 0, "runtime_seconds": 0.0},
    )
    monkeypatch.setattr(
        "evidence_collection.cli.get_collectors",
        lambda sources: [],
    )
    repo.upsert_companies(patch_cli_db, [{"ticker": "MSFT", "company_name": "Microsoft Corporation"}])
    args = type(
        "A",
        (),
        {
            "validation_set": False,
            "ticker": ["MSFT", "ELAN"],
            "all": False,
            "limit": None,
            "source": None,
        },
    )()
    cmd_collect(args)
    companies = repo.get_companies(patch_cli_db, ["MSFT", "ELAN"])
    assert {c["ticker"] for c in companies} == {"MSFT", "ELAN"}
