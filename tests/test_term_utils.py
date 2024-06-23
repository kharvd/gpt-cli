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


def test_parse_with_escape_blocks():
    test_cases = [
        (
            "this is a prompt --bar=1.0 {start}--baz=2.0{end}",
            "this is a prompt  {start}--baz=2.0{end}",
            {"bar": "1.0"},
        ),
        (
            "this is a prompt {start}--bar=1.0{end} --baz=2.0",
            "this is a prompt {start}--bar=1.0{end}",
            {"baz": "2.0"},
        ),
        (
            'this is a prompt --bar=1.0 {start}my first context block{end} and then ```my second context block``` --baz=2.0',
            'this is a prompt  {start}my first context block{end} and then ```my second context block```',
            {'bar': '1.0', 'baz': '2.0'},
        ),
    ]

    delimiters = ["```", '"""', "`"]

    for start, end in [(d, d) for d in delimiters]:
        assert parse_args(f"{start}this is a prompt --bar=1.0 --baz=2.0{end}") == (
            f"{start}this is a prompt --bar=1.0 --baz=2.0{end}",
            {},
        )
        for prompt, expected_prompt, expected_args in test_cases:
            formatted_prompt = prompt.format(start=start, end=end)
            formatted_expected_prompt = expected_prompt.format(start=start, end=end)
            assert parse_args(formatted_prompt) == (
                formatted_expected_prompt,
                expected_args,
            )
