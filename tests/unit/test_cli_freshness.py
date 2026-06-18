import pytest

from evidence_collection.cli import build_parser, cmd_freshness
from evidence_collection.db import repository as repo


@pytest.fixture
def patch_cli_db(conn, tmp_path, monkeypatch):
    db_path = tmp_path / "test.sqlite"
    monkeypatch.setattr(
        "evidence_collection.cli.settings",
        type("S", (), {"db_path": db_path, "log_level": "WARNING"})(),
    )
    return conn


def test_freshness_parser_has_flags():
    parser = build_parser()
    args = parser.parse_args(
        ["freshness", "--pilot-set", "--stale-days", "14", "--json", "--fail-on-stale"]
    )
    assert args.command == "freshness"
    assert args.pilot_set is True
    assert args.stale_days == 14
    assert args.json is True
    assert args.fail_on_stale is True


def test_freshness_empty_db_exits(tmp_path, monkeypatch):
    db_path = tmp_path / "empty.sqlite"
    monkeypatch.setattr(
        "evidence_collection.cli.settings",
        type("S", (), {"db_path": db_path, "log_level": "WARNING"})(),
    )
    with pytest.raises(SystemExit, match="empty"):
        cmd_freshness(type("Args", (), {
            "ticker": None,
            "validation_set": False,
            "pilot_set": False,
            "all": False,
            "stale_days": None,
            "stale_only": False,
            "json": False,
            "output": None,
            "fail_on_stale": False,
        })())


def test_freshness_rejects_multiple_scopes(patch_cli_db):
    repo.upsert_companies(patch_cli_db, [{"ticker": "MSFT", "company_name": "Microsoft"}])
    with pytest.raises(SystemExit, match="exactly one scope"):
        cmd_freshness(type("Args", (), {
            "ticker": ["MSFT"],
            "validation_set": False,
            "pilot_set": True,
            "all": False,
            "stale_days": None,
            "stale_only": False,
            "json": False,
            "output": None,
            "fail_on_stale": False,
        })())


def test_freshness_fail_on_stale(patch_cli_db, monkeypatch):
    repo.upsert_companies(patch_cli_db, [{"ticker": "MSFT", "company_name": "Microsoft"}])
    with pytest.raises(SystemExit) as exc:
        cmd_freshness(type("Args", (), {
            "ticker": ["MSFT"],
            "validation_set": False,
            "pilot_set": False,
            "all": False,
            "stale_days": 30,
            "stale_only": False,
            "json": False,
            "output": None,
            "fail_on_stale": True,
        })())
    assert exc.value.code == 1
