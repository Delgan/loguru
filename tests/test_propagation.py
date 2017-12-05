import logging
import pytest
import sys

def test_formatting(logger, make_logging_logger, capsys):
    fmt = "%(name)s - %(filename)s - %(funcName)s - %(levelname)s - %(levelno)s - %(lineno)d - %(module)s - %(message)s"
    expected = "tests.test_propagation - test_propagation.py - test_formatting - INFO - 20 - 10 - test_propagation - This is my message\n"
    logging_logger = make_logging_logger("tests", sys.stderr, fmt)
    logger.propagate("tests")
    logger.info("This {verb} my {}", "message", verb="is")

    out, err = capsys.readouterr()
    assert out == ""
    assert err == expected

def test_propagate(logger, make_logging_logger, capsys):
    logging_logger = make_logging_logger("tests", sys.stderr)

    logging_logger.debug("1")
    logger.debug("2")

    logger.propagate("tests")

    logger.debug("3")
    logger.trace("4")

    out, err = capsys.readouterr()
    assert out == ""
    assert err == "1\n3\n"

def test_stop_propagation(logger, make_logging_logger, capsys):
    logging_logger = make_logging_logger("tests", sys.stderr)

    logger.propagate("tests.test_propagation")

    logger.debug("1")
    logging_logger.debug("2")

    logger.stop_propagation()

    logger.debug("3")
    logging_logger.debug("4")

    out, err = capsys.readouterr()
    assert out == ""
    assert err == "1\n2\n4\n"

def test_propagate_too_high(logger, make_logging_logger, capsys):
    logging_logger = make_logging_logger("tests.test_propagation", sys.stderr)

    logger.propagate("tests")

    logger.debug("1")
    logging_logger.debug("2")

    out, err = capsys.readouterr()
    assert out == ""
    assert err == "2\n"

def test_multiple_propagate(logger, make_logging_logger, capsys):
    logging_logger = make_logging_logger("tests", sys.stderr)

    logger.propagate("tests.test_propagation")
    logger.debug("1")
    logger.propagate("tests")
    logger.debug("2")

    out, err = capsys.readouterr()
    assert out == ""
    assert err == "1\n2\n"

@pytest.mark.parametrize("use_opt", [False, True])
def test_exception(logger,make_logging_logger, capsys, use_opt):
    logging_logger = make_logging_logger("tests", sys.stderr)
    logger.propagate("tests")

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
