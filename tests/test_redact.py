import re

import pytest

from loguru import logger, redact


def _emit(writer, message, *extra_patterns):
    """Patch ``logger`` with ``redact(*extra_patterns)`` and log ``message``.

    Returns the formatted output captured by ``writer`` (one line, no
    trailing newline).
    """
    logger.remove()
    logger.add(writer, format="{message}")
    logger.patch(redact(*extra_patterns)).info(message)
    return writer.read().rstrip("\n")


def test_redact_is_importable_from_loguru():
    # Spelled out as a separate test so ``from loguru import redact``
    # is exercised even when no logging is performed.
    from loguru import redact as imported

    assert imported is redact


def test_redact_returns_callable_patcher():
    patcher = redact()
    assert callable(patcher)


def test_logger_patch_with_redact_returns_logger_without_raising():
    patched = logger.patch(redact())
    # logger.patch documents a Logger return; we just need a working
    # logger-like object. Smoke-test by issuing a no-op call -- if
    # patch() were to raise, this line would never run.
    assert patched is not None
    assert hasattr(patched, "info")


def test_api_key_value_redacted(writer):
    output = _emit(writer, "api_key=sk-abc123")
    assert "api_key=[REDACTED]" in output
    assert "sk-abc123" not in output


def test_password_value_redacted(writer):
    output = _emit(writer, "password=hunter2")
    assert "password=[REDACTED]" in output
    assert "hunter2" not in output


def test_uri_userinfo_redacted(writer):
    output = _emit(writer, "postgres://alice:s3cr3t@localhost/mydb")
    assert "postgres://[REDACTED]@localhost/mydb" in output
    assert "alice" not in output
    assert "s3cr3t" not in output


def test_authorization_header_redacted(writer):
    output = _emit(writer, "Authorization: Bearer eyJhbGc")
    assert "[REDACTED]" in output
    assert "eyJhbGc" not in output
    # Header name and scheme are preserved.
    assert "Authorization" in output
    assert "Bearer" in output


def test_aws_access_key_redacted(writer):
    output = _emit(writer, "AKIAIOSFODNN7EXAMPLE")
    assert "[REDACTED]" in output
    assert "AKIAIOSFODNN7EXAMPLE" not in output


def test_plain_message_unchanged(writer):
    output = _emit(writer, "hello world")
    assert output == "hello world"
    assert "[REDACTED]" not in output


def test_extra_string_pattern_redacted(writer):
    output = _emit(writer, "MYTOKEN-abc", r"MYTOKEN-\w+")
    assert "[REDACTED]" in output
    assert "MYTOKEN-abc" not in output


def test_extra_compiled_pattern_redacted(writer):
    pattern = re.compile(r"CUSTOM-\d+")
    output = _emit(writer, "value=CUSTOM-42 trailing", pattern)
    assert "[REDACTED]" in output
    assert "CUSTOM-42" not in output
    # Surrounding text must survive.
    assert "trailing" in output


def test_invalid_extra_pattern_raises_at_call_time():
    # ``re.compile`` raises ``re.error`` for invalid sources -- the
    # plan requires this to surface eagerly when ``redact()`` is
    # called, not later at log time.
    with pytest.raises(re.error):
        redact(r"[unclosed")


def test_each_redact_call_returns_independent_patcher():
    p1 = redact()
    p2 = redact(r"FOO")
    assert p1 is not p2
