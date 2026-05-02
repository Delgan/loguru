import re

import pytest

from loguru import logger, redact


def test_redact_preserves_bearer_prefix(writer):
    logger.add(writer, format="{message}")

    logger.patch(redact()).info("Bearer abc.def.ghi")

    assert writer.read() == "Bearer [REDACTED]\n"


def test_redact_preserves_authorization_scheme_prefix(writer):
    logger.add(writer, format="{message}")

    logger.patch(redact()).info("Authorization: Basic dXNlcjpwYXNz")

    assert writer.read() == "Authorization: Basic [REDACTED]\n"


def test_redact_preserves_password_key_case_insensitively(writer):
    logger.add(writer, format="{message}")

    logger.patch(redact()).info("password=hunter2")
    logger.patch(redact()).info("PASSWORD=hunter3")

    assert writer.read().splitlines() == [
        "password=[REDACTED]",
        "PASSWORD=[REDACTED]",
    ]


def test_redact_preserves_token_key(writer):
    logger.add(writer, format="{message}")

    logger.patch(redact()).info("token=opaque-token")

    assert writer.read() == "token=[REDACTED]\n"


def test_redact_preserves_secret_key(writer):
    logger.add(writer, format="{message}")

    logger.patch(redact()).info("secret=top-secret")

    assert writer.read() == "secret=[REDACTED]\n"


def test_redact_replaces_openai_api_key(writer):
    logger.add(writer, format="{message}")

    logger.patch(redact()).info("key sk-abcdefghijklmnopqrstuvwxyz")

    assert writer.read() == "key [REDACTED]\n"


def test_redact_replaces_aws_access_key_id(writer):
    logger.add(writer, format="{message}")

    logger.patch(redact()).info("aws AKIAIOSFODNN7EXAMPLE")

    assert writer.read() == "aws [REDACTED]\n"


def test_redact_replaces_github_pat(writer):
    logger.add(writer, format="{message}")

    logger.patch(redact()).info("github ghp_abcdefghijklmnopqrstuvwxyz1234567890")

    assert writer.read() == "github [REDACTED]\n"


def test_redact_replaces_custom_string_pattern(writer):
    logger.add(writer, format="{message}")

    logger.patch(redact(r"CUST-\d+")).info("prefix CUST-9999 suffix")

    assert writer.read() == "prefix [REDACTED] suffix\n"


def test_redact_replaces_custom_compiled_pattern(writer):
    logger.add(writer, format="{message}")

    logger.patch(redact(re.compile(r"tok_\w+"))).info("prefix tok_abc123 suffix")

    assert writer.read() == "prefix [REDACTED] suffix\n"


def test_redact_leaves_clean_message_unchanged(writer):
    logger.add(writer, format="{message}")

    logger.patch(redact()).info("Nothing sensitive here")

    assert writer.read() == "Nothing sensitive here\n"


def test_redact_rejects_invalid_extra_pattern_type():
    with pytest.raises(TypeError):
        redact(42)
