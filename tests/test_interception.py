import sys
import logging
import pytest

@pytest.fixture
def set_root_logger():
    root_logger = logging.getLogger(None)
    root_level = root_logger.getEffectiveLevel()
    root_logger.setLevel(1)
    yield
    root_logger.setLevel(root_level)

def test_formatting(logger, writer, set_root_logger):
    fmt = "{name} - {file.name} - {function} - {level.name} - {level.no} - {line} - {module} - {message}"
    expected = "tests.a - test_interception.py - test_formatting - DEBUG - 10 - 20 - test_interception - This is the message\n"

    logging_logger = logging.getLogger('tests.a')
    logger.start(writer, format=fmt)
    logger.intercept("tests")
    logging_logger.debug("This is the %s", "message")
    result = writer.read()
    assert result == expected

def test_intercept(logger, writer, set_root_logger):
    ...

def test_stop_interception(logger, make_logging_logger):
    ...

def test_intercept_too_low(logger, make_logging_logger):
    ...

def test_multiple_intercept(logger, make_logging_logger):
    ...

def test_exception(logger, make_logging_logger):
    ...

def test_intercept_twice(logger, make_logging_logger):
    ...

def test_custom_level(logger, make_logging_logger):
    ...

def test_invalid_stopping(logger, make_logging_logger):
    ...

def test_invalid_name(logger):
    ...

def test_not_propagating(logger, make_logging_logger):
    ...
