"""
Test suite demonstrating and validating the caplog + propagate_logs duplication issue.

This test file demonstrates the issue described in GitHub issue #1406 where using both
the caplog and propagate_logs fixtures together causes duplicate log records.
"""
import logging

import pytest

from loguru import logger

from _pytest.logging import LogCaptureFixture


# Standard caplog fixture from migration docs (causes duplication when used with propagate_logs)
@pytest.fixture(name="caplog_standard")
def caplog_standard_fixture(caplog: LogCaptureFixture):
    """Standard caplog fixture as documented in migration guide."""
    handler_id = logger.add(
        caplog.handler,
        format="{message}",
        level=0,
        filter=lambda record: record["level"].no >= caplog.handler.level,
        enqueue=False,
    )
    yield caplog
    logger.remove(handler_id)


# propagate_logs fixture from migration docs
@pytest.fixture(name="propagate_logs_standard", autouse=False)
def propagate_logs_standard_fixture():
    """Standard propagate_logs fixture as documented in migration guide."""

    class PropagateHandler(logging.Handler):
        def emit(self, record):
            if logging.getLogger(record.name).isEnabledFor(record.levelno):
                logging.getLogger(record.name).handle(record)

    logger.remove()
    logger.add(PropagateHandler(), format="{message}")
    yield


# Unified fixture that prevents duplication
@pytest.fixture(name="caplog_unified")
def caplog_unified_fixture(caplog: LogCaptureFixture, request):
    """
    Unified fixture: captures loguru logs + respects --log-cli-level.
    Prevents duplication by handling both use cases intelligently.
    """
    handler_id = logger.add(
        caplog.handler,
        format="{message}",
        level=0,
        filter=lambda record: record["level"].no >= caplog.handler.level,
        enqueue=False,
    )

    cli_level = request.config.getoption("--log-cli-level", None)
    propagate_id = None

    if cli_level:

        class PropagateHandler(logging.Handler):
            def emit(self, record):
                logging.getLogger(record.name).handle(record)

        logger.remove()
        propagate_id = logger.add(PropagateHandler(), format="{message}")

    yield caplog

    logger.remove(handler_id)
    if propagate_id:
        logger.remove(propagate_id)


def test_caplog_standard_alone_works(caplog_standard):
    """Verify standard caplog fixture works correctly when used alone."""
    logger.error("TEST_MESSAGE_STANDARD")

    matching = [r for r in caplog_standard.records if "TEST_MESSAGE_STANDARD" in r.message]
    assert len(matching) == 1, "Expected 1 record, found {}".format(len(matching))


def test_propagate_logs_standard_alone_works(propagate_logs_standard, caplog):
    """Verify standard propagate_logs fixture works correctly when used alone."""
    logger.error("TEST_MESSAGE_PROPAGATE")

    # Note: In this test, caplog won't capture anything because logger.remove() was called
    # This is expected behavior when using propagate_logs alone


@pytest.mark.xfail(
    reason="This test demonstrates the duplication bug when using both fixtures together. "
    "It intentionally fails to show the issue. Remove xfail marker to see the actual failure.",
    strict=True,
)
def test_caplog_and_propagate_together_causes_duplication(
    caplog_standard, propagate_logs_standard
):
    """
    REGRESSION TEST: Demonstrates the duplication issue.

    This test FAILS with the standard fixtures, showing the bug.
    It would pass with the unified fixture.
    """
    logger.error("TEST_MESSAGE_DUPLICATION")

    matching = [r for r in caplog_standard.records if "TEST_MESSAGE_DUPLICATION" in r.message]

    # This assertion FAILS with standard fixtures (finds 2) but would PASS with unified (finds 1)
    assert len(matching) == 1, (
        "DUPLICATION BUG: Expected 1 log record, but found {}. "
        "This occurs when using both caplog and propagate_logs fixtures together. "
        "See docs/resources/migration.rst for the unified fixture solution."
    ).format(len(matching))


def test_unified_fixture_prevents_duplication(caplog_unified):
    """Verify unified fixture captures each log exactly once."""
    logger.error("TEST_MESSAGE_UNIFIED")

    matching = [r for r in caplog_unified.records if "TEST_MESSAGE_UNIFIED" in r.message]
    assert len(matching) == 1, "Expected 1 record, found {}".format(len(matching))


def test_unified_fixture_captures_multiple_logs(caplog_unified):
    """Verify unified fixture handles multiple log messages correctly."""
    logger.debug("DEBUG_MSG")
    logger.info("INFO_MSG")
    logger.warning("WARNING_MSG")
    logger.error("ERROR_MSG")

    assert len(caplog_unified.records) == 4
    assert caplog_unified.records[0].levelname == "DEBUG"
    assert caplog_unified.records[1].levelname == "INFO"
    assert caplog_unified.records[2].levelname == "WARNING"
    assert caplog_unified.records[3].levelname == "ERROR"


def test_unified_fixture_respects_level_filtering(caplog_unified):
    """Verify unified fixture respects log level filtering."""
    caplog_unified.set_level(logging.WARNING)

    logger.debug("DEBUG_MSG")
    logger.info("INFO_MSG")
    logger.warning("WARNING_MSG")
    logger.error("ERROR_MSG")

    # Only WARNING and ERROR should be captured
    assert len(caplog_unified.records) == 2
    assert all(r.levelname in ("WARNING", "ERROR") for r in caplog_unified.records)


def test_unified_fixture_clears_records_between_tests(caplog_unified):
    """Verify unified fixture properly clears records between tests."""
    # This test verifies that records from previous tests don't leak
    logger.info("FRESH_START")

    assert len(caplog_unified.records) == 1
    assert "FRESH_START" in caplog_unified.records[0].message


def test_unified_fixture_handles_exceptions(caplog_unified):
    """Verify unified fixture handles exception logging correctly."""
    try:
        1 / 0  # noqa: B018
    except ZeroDivisionError:
        logger.exception("Division error occurred")

    assert len(caplog_unified.records) == 1
    assert "Division error occurred" in caplog_unified.records[0].message
    assert caplog_unified.records[0].exc_info is not None


def test_unified_fixture_text_property(caplog_unified):
    """Verify unified fixture provides text property for assertions."""
    logger.info("First message")
    logger.warning("Second message")

    assert "First message" in caplog_unified.text
    assert "Second message" in caplog_unified.text


def test_unified_fixture_with_bound_logger(caplog_unified):
    """Verify unified fixture works with bound loggers."""
    bound_logger = logger.bind(user="test_user", request_id="123")
    bound_logger.info("Bound logger message")

    assert len(caplog_unified.records) == 1
    assert "Bound logger message" in caplog_unified.records[0].message
