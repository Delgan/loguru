import logging
import pickle
import sys
import datetime

import pytest

from loguru import logger


class StreamHandler:
    def __init__(self, flushable=False, stoppable=False):
        if flushable:
            self.flush = self._flush
        if stoppable:
            self.stop = self._stop

        self.wrote = ""
        self.flushed = False
        self.stopped = False

    def write(self, message):
        self.wrote += message

    def _flush(self):
        self.flushed = True

    def _stop(self):
        self.stopped = True


class StandardHandler(logging.Handler):
    def __init__(self, level):
        super().__init__(level)
        self.written = ""
        self.lock = None

    def emit(self, record):
        self.written += record.getMessage()

    def acquire(self):
        pass

    def createLock(self):
        return None


def format_function(record):
    return "-> {message}"


def filter_function(record):
    return "[PASS]" in record["message"]


def patch_function(record):
    record["extra"]["foo"] = "bar"


def rotation_function(message, file):
    pass


def retention_function(files):
    pass


def compression_function(path):
    pass


def test_pickling_function_handler(capsys):
    logger.add(print, format="{level} - {function} - {message}", end="")
    pickled = pickle.dumps(logger)
    unpikcled = pickle.loads(pickled)
    unpikcled.debug("A message")
    out, err = capsys.readouterr()
    assert out == "DEBUG - test_pickling_function_handler - A message\n"
    assert err == ""


@pytest.mark.parametrize("flushable", [True, False])
@pytest.mark.parametrize("stoppable", [True, False])
def test_pickling_stream_handler(flushable, stoppable):
    stream = StreamHandler(flushable, stoppable)
    i = logger.add(stream, format="{level} - {function} - {message}")
    pickled = pickle.dumps(logger)
    unpickled = pickle.loads(pickled)
    unpickled.debug("A message")
    stream = next(iter(unpickled._core.handlers.values()))._sink._stream
    unpickled.remove(i)
    assert stream.wrote == "DEBUG - test_pickling_stream_handler - A message\n"
    assert stream.flushed == flushable
    assert stream.stopped == stoppable


def test_pickling_standard_handler():
    handler = StandardHandler(logging.NOTSET)
    logger.add(handler, format="{level} - {function} - {message}")
    pickled = pickle.dumps(logger)
    unpickled = pickle.loads(pickled)
    unpickled.debug("A message")
    handler = next(iter(unpickled._core.handlers.values()))._sink._handler
    assert handler.written == "DEBUG - test_pickling_standard_handler - A message"


def test_pickling_class_handler():
    logger.add(StreamHandler, format="{level} - {function} - {message}")
    pickled = pickle.dumps(logger)
    unpickled = pickle.loads(pickled)
    unpickled.debug("A message")
    stream = next(iter(unpickled._core.handlers.values()))._sink._stream
    assert stream.wrote == "DEBUG - test_pickling_class_handler - A message\n"


def test_pickling_file_handler(tmpdir):
    file = tmpdir.join("test.log")
    logger.add(str(file), format="{level} - {function} - {message}", delay=True)
    pickled = pickle.dumps(logger)
    unpickled = pickle.loads(pickled)
    unpickled.debug("A message")
    assert file.read() == "DEBUG - test_pickling_file_handler - A message\n"


@pytest.mark.parametrize(
    "rotation",
    [
        1000,
        "daily",
        datetime.timedelta(minutes=60),
        datetime.time(hour=12, minute=00, second=00),
        "200 MB",
        "10:00",
        "5 hours",
        rotation_function,
    ],
)
def test_pickling_file_handler_rotation(tmpdir, rotation):
    file = tmpdir.join("test.log")
    logger.add(str(file), format="{level} - {function} - {message}", delay=True, rotation=rotation)
    pickled = pickle.dumps(logger)
    unpickled = pickle.loads(pickled)
    unpickled.debug("A message")
    assert file.read() == "DEBUG - test_pickling_file_handler_rotation - A message\n"


@pytest.mark.parametrize(
    "retention", [1000, datetime.timedelta(hours=13), "10 days", retention_function]
)
def test_pickling_file_handler_retention(tmpdir, retention):
    file = tmpdir.join("test.log")
    logger.add(
        str(file), format="{level} - {function} - {message}", delay=True, retention=retention
    )
    pickled = pickle.dumps(logger)
    unpickled = pickle.loads(pickled)
    unpickled.debug("A message")
    assert file.read() == "DEBUG - test_pickling_file_handler_retention - A message\n"


@pytest.mark.parametrize("compression", ["zip", "gz", "tar", compression_function])
def test_pickling_file_handler_compression(tmpdir, compression):
    file = tmpdir.join("test.log")
    logger.add(
        str(file), format="{level} - {function} - {message}", delay=True, compression=compression
    )
    pickled = pickle.dumps(logger)
    unpickled = pickle.loads(pickled)
    unpickled.debug("A message")
    assert file.read() == "DEBUG - test_pickling_file_handler_compression - A message\n"


def test_pickling_no_handler(writer):
    pickled = pickle.dumps(logger)
    unpickled = pickle.loads(pickled)
    unpickled.add(writer, format="{level} - {function} - {message}")
    unpickled.debug("A message")
    assert writer.read() == "DEBUG - test_pickling_no_handler - A message\n"


def test_pickling_handler_not_serializable():
    logger.add(lambda m: None)
    with pytest.raises(ValueError, match="The logger can't be pickled"):
        pickle.dumps(logger)


def test_pickling_filter_function(capsys):
    logger.add(print, format="{message}", filter=filter_function, end="")
    pickled = pickle.dumps(logger)
    unpickled = pickle.loads(pickled)
    unpickled.info("Nope")
    unpickled.info("[PASS] Yes")
    out, err = capsys.readouterr()
    assert out == "[PASS] Yes\n"
    assert err == ""


@pytest.mark.parametrize("filter", ["", "tests"])
def test_pickling_filter_name(capsys, filter):
    logger.add(print, format="{message}", filter=filter, end="")
    pickled = pickle.dumps(logger)
    unpickled = pickle.loads(pickled)
    unpickled.info("A message")
    out, err = capsys.readouterr()
    assert out == "A message\n"
    assert err == ""


def test_pickling_format_function(capsys):
    logger.add(print, format=format_function, end="")
    pickled = pickle.dumps(logger)
    unpickled = pickle.loads(pickled)
    unpickled.info("The message")
    out, err = capsys.readouterr()
    assert out == "-> The message"
    assert err == ""


def test_pickling_filter_function_not_serializable():
    logger.add(print, filter=lambda r: True)
    with pytest.raises(ValueError, match="The logger can't be pickled"):
        pickle.dumps(logger)


def test_pickling_format_function_not_serializable():
    logger.add(print, format=lambda r: "{message}")
    with pytest.raises(ValueError, match="The logger can't be pickled"):
        pickle.dumps(logger)


def test_pickling_bound_logger(writer):
    bound_logger = logger.bind(foo="bar")
    pickled = pickle.dumps(bound_logger)
    unpickled = pickle.loads(pickled)
    unpickled.add(writer, format="{extra[foo]}")
    unpickled.info("Test")
    assert writer.read() == "bar\n"


def test_pickling_patched_logger(writer):
    patched_logger = logger.patch(patch_function)
    pickled = pickle.dumps(patched_logger)
    unpickled = pickle.loads(pickled)
    unpickled.add(writer, format="{extra[foo]}")
    unpickled.info("Test")
    assert writer.read() == "bar\n"


def test_remove_after_pickling(capsys):
    i = logger.add(print, end="", format="{message}")
    logger.info("A")
    pickled = pickle.dumps(logger)
    unpickled = pickle.loads(pickled)
    unpickled.remove(i)
    unpickled.info("B")
    out, err = capsys.readouterr()
    assert out == "A\n"
    assert err == ""


def test_pickling_logging_method(capsys):
    logger.add(print, format="{level} - {function} - {message}", end="")
    pickled = pickle.dumps(logger.critical)
    func = pickle.loads(pickled)
    func("A message")
    out, err = capsys.readouterr()
    assert out == "CRITICAL - test_pickling_logging_method - A message\n"
    assert err == ""


def test_pickling_log_method(capsys):
    logger.add(print, format="{level} - {function} - {message}", end="")
    pickled = pickle.dumps(logger.log)
    func = pickle.loads(pickled)
    func(19, "A message")
    out, err = capsys.readouterr()
    assert out == "Level 19 - test_pickling_log_method - A message\n"
    assert err == ""


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
