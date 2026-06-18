import pytest

from evidence_collection.cli import build_parser, cmd_collect


def test_collect_parser_has_validation_set_flag():
    parser = build_parser()
    args = parser.parse_args(["collect", "--validation-set"])
    assert args.validation_set is True
    assert args.command == "collect"


def test_load_companies_parser_has_validation_set_flag():
    parser = build_parser()
    args = parser.parse_args(["load-companies", "--validation-set"])
    assert args.validation_set is True


def test_collect_parser_has_pilot_set_flag():
    parser = build_parser()
    args = parser.parse_args(["collect", "--pilot-set"])
    assert args.pilot_set is True


def test_collect_rejects_validation_set_with_ticker():
    parser = build_parser()
    args = parser.parse_args(["collect", "--validation-set", "--ticker", "MSFT"])
    with pytest.raises(SystemExit, match="exactly one scope"):
        cmd_collect(args)


def test_collect_rejects_validation_set_with_all():
    parser = build_parser()
    args = parser.parse_args(["collect", "--validation-set", "--all"])
    with pytest.raises(SystemExit, match="exactly one scope"):
        cmd_collect(args)


def test_collect_rejects_pilot_set_with_limit():
    parser = build_parser()
    args = parser.parse_args(["collect", "--pilot-set", "--limit", "10"])
    with pytest.raises(SystemExit, match="exactly one scope"):
        cmd_collect(args)
