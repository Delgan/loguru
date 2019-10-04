from loguru import logger
import pickle
import sys
import pytest


@pytest.mark.xfail(reason="Not yet implemented")
def test_pickling_logging_method(capsys):
    logger.add(print, format="{level} - {function} - {message}")
    pickled = pickle.dumps(logger.critical)
    func = pickle.loads(pickled)
    func("A message")
    out, err = capsys.readouterr()
    assert out == "CRITICAL - test_pickling_logging_method - A message\n"
    assert err == ""


@pytest.mark.xfail(reason="Not yet implemented")
def test_pickling_log_method(capsys):
    logger.add(print, format="{level} - {function} - {message}")
    pickled = pickle.dumps(logger.log)
    func = pickle.loads(pickled)
    func(19, "A message")
    out, err = capsys.readouterr()
    assert out == "Level 19 - test_pickling_log_method - A message\n"
    assert err == ""


@pytest.mark.xfail(reason="Not yet implemented")
def test_pickling_logger_no_handler(writer):
    pickled = pickle.dumps(logger)
    inst = pickle.loads(pickled)
    inst.add(writer, format="{level} - {function} - {message}")
    inst.debug("A message")
    assert writer.read() == "DEBUG - test_pickling_logger - A message\n"


@pytest.mark.xfail(reason="Not yet implemented")
def test_pickling_logger_handler_serializable(capsys):
    logger.add(print)
    pickled = pickle.dumps(logger)
    inst = pickle.loads(pickled)
    inst.debug("A message")
    out, err = capsys.readouterr()
    assert out == "DEBUG - test_pickling_logger - A message\n"
    assert err == ""


@pytest.mark.xfail(reason="Not yet implemented")
def test_pickling_logger_handler_not_serializable():
    logger.add(lambda m: None)
    with pytest.raises(ValueError, match="The logger can't be pickled"):
        pickle.dumps(logger)


@pytest.mark.xfail(reason="Not yet implemented")
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
