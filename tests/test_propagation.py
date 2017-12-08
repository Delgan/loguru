import logging
import pytest
import sys
from loguru import logger
from logging import StreamHandler

def propagate_sink(message):
    record = message.record
    logging_logger = logging.getLogger(record['name'])
    logging_record = logging_logger.makeRecord(
        record['name'], record['level'].no, record['file'].path, record['line'], record['message'],
        [], message.exception, record['function'], logger.extra, None)
    logging_logger.handle(logging_record)

def test_formatting(make_logging_logger, capsys):
    fmt = "%(name)s - %(filename)s - %(funcName)s - %(levelname)s - %(levelno)s - %(lineno)d - %(module)s - %(message)s"
    expected = "tests.test_propagation - test_propagation.py - test_formatting - DEBUG - 10 - 20 - test_propagation - This is my message\n"
    logging_logger = make_logging_logger(None, StreamHandler(sys.stderr), fmt)
    logger.start(propagate_sink)
    logger.debug("This {verb} my {}", "message", verb="is")

    out, err = capsys.readouterr()
    assert out == ""
    assert err == expected

def test_propagate(make_logging_logger, capsys):
    logging_logger = make_logging_logger("tests", StreamHandler(sys.stderr))

    logging_logger.debug("1")
    logger.debug("2")

    logger.start(propagate_sink)

    logger.debug("3")
    logger.trace("4")

    out, err = capsys.readouterr()
    assert out == ""
    assert err == "1\n3\n"

def test_stop_propagation(make_logging_logger, capsys):
    logging_logger = make_logging_logger("tests", StreamHandler(sys.stderr))

    i = logger.start(propagate_sink)

    logger.debug("1")
    logging_logger.debug("2")

    logger.stop(i)

    logger.debug("3")
    logging_logger.debug("4")

    out, err = capsys.readouterr()
    assert out == ""
    assert err == "1\n2\n4\n"

def test_propagate_too_high(make_logging_logger, capsys):
    logging_logger = make_logging_logger("tests.test_propagation.deep", StreamHandler(sys.stderr))

    logger.start(propagate_sink)

    logger.debug("1")
    logging_logger.debug("2")

    out, err = capsys.readouterr()
    assert out == ""
    assert err == "2\n"

@pytest.mark.parametrize("use_opt", [False, True])
def test_exception(make_logging_logger, capsys, use_opt):
    logging_logger = make_logging_logger("tests", StreamHandler(sys.stderr))
    logger.start(propagate_sink)

    try:
        1 / 0
    except:
        if use_opt:
            logger.opt(exception=True).error("Oops...")
        else:
            logger.exception("Oops...")

    out, err = capsys.readouterr()
    lines = err.strip().splitlines()

    assert out == ""
    assert lines[0] == "Oops..."
    assert lines[-1] == "ZeroDivisionError: division by zero"
