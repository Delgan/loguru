import logging
import pytest
import sys
from loguru import logger
from logging import StreamHandler


class PropagateHandler(logging.Handler):
    def emit(self, record):
        logging.getLogger(record.name).handle(record)


def test_formatting(make_logging_logger, capsys):
    fmt = "%(name)s - %(filename)s - %(funcName)s - %(levelname)s - %(levelno)s - %(lineno)d - %(module)s - %(message)s"
    expected = "tests.test_propagation - test_propagation.py - test_formatting - DEBUG - 10 - 18 - test_propagation - This is my message\n"
    make_logging_logger("tests.test_propagation", StreamHandler(sys.stderr), fmt)
    logger.add(PropagateHandler(), format="{message}")
    logger.debug("This {verb} my {}", "message", verb="is")

    out, err = capsys.readouterr()
    assert out == ""
    assert err == expected


def test_propagate(make_logging_logger, capsys):
    logging_logger = make_logging_logger("tests", StreamHandler(sys.stderr))

    logging_logger.debug("1")
    logger.debug("2")

    logger.add(PropagateHandler(), format="{message}")

    logger.debug("3")
    logger.trace("4")

    out, err = capsys.readouterr()
    assert out == ""
    assert err == "1\n3\n"


def test_remove_propagation(make_logging_logger, capsys):
    logging_logger = make_logging_logger("tests", StreamHandler(sys.stderr))

    i = logger.add(PropagateHandler(), format="{message}")

    logger.debug("1")
    logging_logger.debug("2")

    logger.remove(i)

    logger.debug("3")
    logging_logger.debug("4")

    out, err = capsys.readouterr()
    assert out == ""
    assert err == "1\n2\n4\n"


def test_propagate_too_high(make_logging_logger, capsys):
    logging_logger = make_logging_logger("tests.test_propagation.deep", StreamHandler(sys.stderr))

    logger.add(PropagateHandler(), format="{message}")

    logger.debug("1")
    logging_logger.debug("2")

    out, err = capsys.readouterr()
    assert out == ""
    assert err == "2\n"


@pytest.mark.parametrize("use_opt", [False, True])
def test_exception(make_logging_logger, capsys, use_opt):
    make_logging_logger("tests", StreamHandler(sys.stderr))
    logger.add(PropagateHandler(), format="{message}")

    try:
        1 / 0
    except:
        if use_opt:
            logger.opt(exception=True).error("Oops...")
        else:
            logger.exception("Oops...")

    out, err = capsys.readouterr()
    lines = err.strip().splitlines()

    error = "ZeroDivisionError: division by zero"

    assert out == ""
    assert lines[0] == "Oops..."
    assert lines[-1] == error
    assert err.count(error) == 1
