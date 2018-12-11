import sys
import logging
import pytest

from loguru import logger


class InterceptHandler(logging.Handler):
    def emit(self, record):
        logger.opt(depth=6, exception=record.exc_info).log(record.levelno, record.getMessage())


def test_formatting(writer, make_logging_logger):
    fmt = "{name} - {file.name} - {function} - {level.name} - {level.no} - {line} - {module} - {message}"
    expected = "tests.test_interception - test_interception.py - test_formatting - Level 10 - 10 - 21 - test_interception - This is the message\n"

    logging_logger = make_logging_logger("tests", InterceptHandler())

    logger.add(writer, format=fmt)

    logging_logger.debug("This is the %s", "message")

    result = writer.read()
    assert result == expected


def test_intercept(writer, make_logging_logger):
    logging_logger = make_logging_logger(None, InterceptHandler())

    logging_logger.info("Nope")

    logger.add(writer, format="{message}")

    logging_logger.info("Test")

    result = writer.read()
    assert result == "Test\n"


def test_add_before_intercept(writer, make_logging_logger):
    logger.add(writer, format="{message}")
    logging_logger = make_logging_logger(None, InterceptHandler())

    logging_logger.info("Test")

    result = writer.read()
    assert result == "Test\n"


def test_remove_interception(writer, make_logging_logger):
    h = InterceptHandler()
    logging_logger = make_logging_logger("foobar", h)
    logger.add(writer, format="{message}")
    logging_logger.debug("1")
    logging_logger.removeHandler(h)
    logging_logger.debug("2")

    result = writer.read()
    assert result == "1\n"


def test_intercept_too_low(writer, make_logging_logger):
    logging_logger = make_logging_logger("tests.test_interception", InterceptHandler())
    logger.add(writer, format="{message}")
    logging.getLogger("tests").error("Nope 1")
    logging.getLogger("foobar").error("Nope 2")
    result = writer.read()
    assert result == ""


def test_multiple_intercept(writer, make_logging_logger):
    logging_logger_1 = make_logging_logger("test_1", InterceptHandler())
    logging_logger_2 = make_logging_logger("test_2", InterceptHandler())

    logger.add(writer, format="{message}")

    logging_logger_1.info("1")
    logging_logger_2.info("2")

    result = writer.read()
    assert result == "1\n2\n"


def test_exception(writer, make_logging_logger):
    logging_logger = make_logging_logger("tests.test_interception", InterceptHandler())
    logger.add(writer, format="{message}")

    try:
        1 / 0
    except:
        logging_logger.exception("Oops...")

    lines = writer.read().strip().splitlines()
    assert lines[0] == "Oops..."
    assert lines[-1] == "ZeroDivisionError: division by zero"
    assert sum(line.startswith("> ") for line in lines) == 1


def test_log_level(writer, make_logging_logger):
    logging_logger = make_logging_logger("tests", InterceptHandler())
    logger.add(writer, format="{level.no} - {level.name} - {message}")

    logging_logger.log(12, "Hop")

    result = writer.read()
    assert result == "12 - Level 12 - Hop\n"
