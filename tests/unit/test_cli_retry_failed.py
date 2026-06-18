from evidence_collection.cli import build_parser, cmd_retry_failed


def test_retry_failed_parser_has_flags():
    parser = build_parser()
    args = parser.parse_args(["retry-failed", "--dry-run", "--source", "research"])
    assert args.command == "retry-failed"
    assert args.dry_run is True
    assert args.source == ["research"]


def test_retry_failed_dry_run_empty_db(capsys, conn, tmp_path, monkeypatch):
    monkeypatch.setenv("AI_DEPTH_DB", str(tmp_path / "dry.sqlite"))
    from evidence_collection.db import apply_migrations, connect

    db = tmp_path / "dry.sqlite"
    c = connect(db)
    apply_migrations(c)
    c.close()

    cmd_retry_failed(type("Args", (), {"ticker": None, "source": None, "dry_run": True})())
    out = capsys.readouterr().out
    assert "No retryable" in out or "0 pair(s)" in out
