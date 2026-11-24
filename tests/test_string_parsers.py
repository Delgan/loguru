from loguru._string_parsers import parse_size


def test_parse_size_exa_units():
    assert parse_size("1EB") == 1e18
    assert parse_size("1EiB") == 1024**6
    assert parse_size("1e3MB") == 1e9
