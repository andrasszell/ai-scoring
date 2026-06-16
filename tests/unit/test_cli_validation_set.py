from evidence_collection.cli import build_parser


def test_collect_parser_has_validation_set_flag():
    parser = build_parser()
    args = parser.parse_args(["collect", "--validation-set"])
    assert args.validation_set is True
    assert args.command == "collect"


def test_load_companies_parser_has_validation_set_flag():
    parser = build_parser()
    args = parser.parse_args(["load-companies", "--validation-set"])
    assert args.validation_set is True
