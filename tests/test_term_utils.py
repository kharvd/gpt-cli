from gptcli.cli import parse_args


def test_parse_args():
    assert parse_args("foo") == ("foo", {})
    assert parse_args("foo bar") == ("foo bar", {})
    # Check with space delimitation
    assert parse_args("--novelKey 2.0 foo bar") == (
        "foo bar",
        {"novelKey": "2.0"},
    )
    # Check with equal elimination
    assert parse_args("--novelKey=2.0 foo bar") == (
        "foo bar",
        {"novelKey": "2.0"},
    )
    # String option
    assert parse_args("--novelKey Tes:t-Str_i--ng foo bar") == (
        "foo bar",
        {"novelKey": "Tes:t-Str_i--ng"},
    )
    # Colon based flag
    assert parse_args(":novelKey 2.0 foo bar") == (
        "foo bar",
        {"novelKey": "2.0"},
    )
    assert parse_args(":novelKey Tes:t-Str_i--ng foo bar") == (
        "foo bar",
        {"novelKey": "Tes:t-Str_i--ng"},
    )
    assert parse_args("--novelKey1=2.0 :novelKey2 Tes:t-Str_i--ng --novelKey3=fizz foo bar") == (
        "foo bar",
        {
            "novelKey1": "2.0",
            "novelKey2": "Tes:t-Str_i--ng",
            "novelKey3": "fizz",
        },
    )
    # Allow "flags" to appear in prompt
    assert parse_args("--novelKey1=2.0 :novelKey2 Tes:t-Str_i--ng "\
                      "--novelKey3=fizz foo bar --notAKey badVal") == (
        "foo bar --notAKey badVal",
        {
            "novelKey1": "2.0",
            "novelKey2": "Tes:t-Str_i--ng",
            "novelKey3": "fizz",
        },
    )
    # No key tests
    assert parse_args("foobar --novelKey1=2.0 :novelKey2 Tes:t-Str_i--ng ") == (
        "foobar --novelKey1=2.0 :novelKey2 Tes:t-Str_i--ng ", {}
    )
    assert parse_args("-- foobar --novelKey1=2.0 :novelKey2 Tes:t-Str_i--ng ") == (
        "-- foobar --novelKey1=2.0 :novelKey2 Tes:t-Str_i--ng ", {}
    )
    assert parse_args(": foobar --novelKey1=2.0 :novelKey2 Tes:t-Str_i--ng ") == (
        ": foobar --novelKey1=2.0 :novelKey2 Tes:t-Str_i--ng ", {}
    )
    # Other symbol
    assert parse_args("*foobar --novelKey1=2.0 :novelKey2 Tes:t-Str_i--ng ") == (
        "*foobar --novelKey1=2.0 :novelKey2 Tes:t-Str_i--ng ", {}
    )
