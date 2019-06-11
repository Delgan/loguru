from loguru import logger
import pickle
import sys
import pytest


def test_pickling_logging_method(writer):
    logger.add(writer, format="{level} - {function} - {message}")
    pickled = pickle.dumps(logger.critical)
    func = pickle.loads(pickled)
    func("A message")
    assert writer.read() == "CRITICAL - test_pickling_logging_method - A message\n"


def test_pickling_log_method(writer):
    logger.add(writer, format="{level} - {function} - {message}")
    pickled = pickle.dumps(logger.log)
    func = pickle.loads(pickled)
    func(19, "A message")
    assert writer.read() == "Level 19 - test_pickling_log_method - A message\n"


def test_pickling_logger(writer):
    pickled = pickle.dumps(logger)
    inst = pickle.loads(pickled)
    inst.add(writer, format="{level} - {function} - {message}")
    inst.debug("A message")
    assert writer.read() == "DEBUG - test_pickling_logger - A message\n"


@pytest.mark.parametrize(
    "method",
    [
        logger.add,
        logger.remove,
        logger.catch,
        logger.opt,
        logger.bind,
        logger.patch,
        logger.level,
        logger.disable,
        logger.enable,
        logger.configure,
        logger.parse,
        logger.exception,
    ],
)
def test_pickling_no_error(method):
    pickled = pickle.dumps(method)
    unpickled = pickle.loads(pickled)
    assert unpickled
