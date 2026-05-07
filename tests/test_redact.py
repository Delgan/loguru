import re

import pytest

from loguru import logger, redact


@pytest.mark.parametrize("key", ["api_key", "password", "token", "secret"])
@pytest.mark.parametrize("separator", ["=", ":"])
def test_redact_builtin_key_value_patterns_preserve_key(writer, key, separator):
    logger.add(writer, format="{message}")

    logger.patch(redact()).info("%s%svalue" % (key, separator))

    assert writer.read() == "%s%s[REDACTED]\n" % (key, separator)


def test_redact_builtin_bearer_pattern_preserves_scheme(writer):
    logger.add(writer, format="{message}")

    logger.patch(redact()).info("Bearer token123")

    assert writer.read() == "Bearer [REDACTED]\n"


def test_redact_builtin_aws_key_pattern_replaces_key(writer):
    logger.add(writer, format="{message}")

    logger.patch(redact()).info("aws key AKIAABCDEFGHIJKLMNOP is active")

    assert writer.read() == "aws key [REDACTED] is active\n"


def test_redact_builtin_connection_string_secret_preserves_prefix(writer):
    logger.add(writer, format="{message}")

    logger.patch(redact()).info("postgres://db.example/app?password=s3cret&ssl=true")

    assert writer.read() == "postgres://db.example/app?password=[REDACTED]&ssl=true\n"


@pytest.mark.parametrize("scheme", ["Bearer", "Basic", "Token"])
def test_redact_builtin_authorization_pattern_preserves_prefix(writer, scheme):
    logger.add(writer, format="{message}")

    logger.patch(redact()).info("Authorization: %s credential123" % scheme)

    assert writer.read() == "Authorization: %s [REDACTED]\n" % scheme


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("API_KEY=foo", "API_KEY=[REDACTED]\n"),
        ("Password=bar", "Password=[REDACTED]\n"),
        ("BEARER token123", "BEARER [REDACTED]\n"),
    ],
)
def test_redact_builtin_patterns_are_case_insensitive(writer, message, expected):
    logger.add(writer, format="{message}")

    logger.patch(redact()).info(message)

    assert writer.read() == expected


def test_redact_string_extra_pattern_replaces_full_match(writer):
    logger.add(writer, format="{message}")

    logger.patch(redact(r"my_token_\w+")).info("prefix my_token_abc123 suffix")

    assert writer.read() == "prefix [REDACTED] suffix\n"


def test_redact_compiled_extra_pattern_replaces_full_match(writer):
    logger.add(writer, format="{message}")

    logger.patch(redact(re.compile(r"SECRET", re.IGNORECASE))).info("prefix secret suffix")

    assert writer.read() == "prefix [REDACTED] suffix\n"


def test_redact_multiple_extra_patterns(writer):
    logger.add(writer, format="{message}")

    logger.patch(redact(r"foo", r"bar")).info("foo baz bar")

    assert writer.read() == "[REDACTED] baz [REDACTED]\n"


def test_redact_multiple_builtin_secrets_in_one_message(writer):
    logger.add(writer, format="{message}")

    logger.patch(redact()).info("api_key=abc password=s3cret Bearer token123")

    assert writer.read() == "api_key=[REDACTED] password=[REDACTED] Bearer [REDACTED]\n"


def test_redact_leaves_clean_message_unchanged(writer):
    logger.add(writer, format="{message}")

    logger.patch(redact()).info("Nothing sensitive here")

    assert writer.read() == "Nothing sensitive here\n"


def test_redact_empty_message_does_not_error(writer):
    logger.add(writer, format="{message}")

    logger.patch(redact()).info("")

    assert writer.read() == "\n"


def test_redact_chains_with_other_redact_patchers(writer):
    logger.add(writer, format="{message}")

    logger.patch(redact()).patch(redact(r"extra")).info("password=secret extra")

    assert writer.read() == "password=[REDACTED] [REDACTED]\n"


def test_redact_patched_logger_does_not_affect_original_logger(writer):
    logger.add(writer, format="{message}")

    patched_logger = logger.patch(redact())
    patched_logger.info("password=secret")
    logger.info("password=secret")

    assert writer.read().splitlines() == [
        "password=[REDACTED]",
        "password=secret",
    ]


def test_redact_returns_callable():
    assert callable(redact())
    assert callable(redact(r"x"))


def test_redact_rejects_invalid_extra_pattern_type():
    with pytest.raises(TypeError):
        redact(42)
