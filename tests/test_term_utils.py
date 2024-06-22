from gptcli.cli import parse_args


def test_parse_args():
    assert parse_args("foo") == ("foo", {})
    assert parse_args("foo bar") == ("foo bar", {})
    assert parse_args("this is a prompt --bar 1.0") == (
        "this is a prompt",
        {"bar": "1.0"},
    )
    assert parse_args("this is a prompt --bar 1.0 --baz    2.0") == (
        "this is a prompt",
        {"bar": "1.0", "baz": "2.0"},
    )
    assert parse_args("this is a prompt --bar=1.0 --baz=2.0") == (
        "this is a prompt",
        {"bar": "1.0", "baz": "2.0"},
    )
    assert parse_args("```this is a prompt --bar=1.0 --baz=2.0```") == (
        "this is a prompt --bar=1.0 --baz=2.0",
        {},
    )
    assert parse_args("this is a prompt --bar=1.0 ```--baz=2.0```") == (
        "this is a prompt  --baz=2.0",
        {"bar": "1.0"},
    )
    assert parse_args("this is a prompt ```--bar=1.0``` --baz=2.0") == (
        "this is a prompt --bar=1.0",
        {"baz": "2.0"},
    )
    assert parse_args('"""this is a prompt --bar=3.0 --baz=4.0"""') == (
        "this is a prompt --bar=3.0 --baz=4.0",
        {},
    )
    assert parse_args('this is a prompt --bar=1.0 """--baz=2.0"""') == (
        "this is a prompt  --baz=2.0",
        {"bar": "1.0"},
    )