from evidence_collection.cli import build_parser


def test_snapshot_parser_has_flags():
    parser = build_parser()
    args = parser.parse_args(
        ["snapshot", "--tag", "phase3_sp500", "--output-dir", "data/exports/snapshots/x"]
    )
    assert args.command == "snapshot"
    assert args.tag == "phase3_sp500"
    assert args.output_dir == "data/exports/snapshots/x"
