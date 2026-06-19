from evidence_collection.cli import build_parser


def test_coverage_parser_has_flags():
    parser = build_parser()
    args = parser.parse_args(["coverage", "--missing-only", "--json"])
    assert args.command == "coverage"
    assert args.missing_only is True
    assert args.json is True
