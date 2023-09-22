import asyncio
import datetime
import logging
import pickle

import pytest

from loguru import logger

from .conftest import parse


def print_(message):
    print(message, end="")


async def async_print(msg):
    print_(msg)


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

    def createLock(self):  # noqa: N802
        return None


def format_function(record):
    return "-> <red>{message}</red>"


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
    logger.add(print_, format="{level} - {function} - {message}")
    pickled = pickle.dumps(logger)
    unpikcled = pickle.loads(pickled)
    unpikcled.debug("A message")
    out, err = capsys.readouterr()
    assert out == "DEBUG - test_pickling_function_handler - A message\n"
    assert err == ""


def test_pickling_coroutine_function_handler(capsys):
    logger.add(async_print, format="{level} - {function} - {message}")
    pickled = pickle.dumps(logger)
    unpikcled = pickle.loads(pickled)

    async def async_debug():
        unpikcled.debug("A message")
        await unpikcled.complete()

    asyncio.run(async_debug())

    out, err = capsys.readouterr()
    assert out == "DEBUG - async_debug - A message\n"
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


def test_pickling_standard_handler_root_logger_not_picklable(monkeypatch, capsys):
    def reduce_protocol():
        raise TypeError("Not picklable")

    with monkeypatch.context() as context:
        context.setattr(logging.getLogger(), "__reduce__", reduce_protocol, raising=False)

        handler = StandardHandler(logging.NOTSET)
        logger.add(handler, format="=> {message}", catch=False)

        pickled = pickle.dumps(logger)
        pickle.loads(pickled)

        logger.info("Ok")
        out, err = capsys.readouterr()
        assert out == ""
        assert err == ""
        assert handler.written == "=> Ok"


def test_pickling_file_handler(tmp_path):
    file = tmp_path / "test.log"
    logger.add(file, format="{level} - {function} - {message}", delay=True)
    pickled = pickle.dumps(logger)
    unpickled = pickle.loads(pickled)
    unpickled.debug("A message")
    assert file.read_text() == "DEBUG - test_pickling_file_handler - A message\n"


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
def test_pickling_file_handler_rotation(tmp_path, rotation):
    file = tmp_path / "test.log"
    logger.add(file, format="{level} - {function} - {message}", delay=True, rotation=rotation)
    pickled = pickle.dumps(logger)
    unpickled = pickle.loads(pickled)
    unpickled.debug("A message")
    assert file.read_text() == "DEBUG - test_pickling_file_handler_rotation - A message\n"


@pytest.mark.parametrize(
    "retention", [1000, datetime.timedelta(hours=13), "10 days", retention_function]
)
def test_pickling_file_handler_retention(tmp_path, retention):
    file = tmp_path / "test.log"
    logger.add(file, format="{level} - {function} - {message}", delay=True, retention=retention)
    pickled = pickle.dumps(logger)
    unpickled = pickle.loads(pickled)
    unpickled.debug("A message")
    assert file.read_text() == "DEBUG - test_pickling_file_handler_retention - A message\n"


@pytest.mark.parametrize("compression", ["zip", "gz", "tar", compression_function])
def test_pickling_file_handler_compression(tmp_path, compression):
    file = tmp_path / "test.log"
    logger.add(file, format="{level} - {function} - {message}", delay=True, compression=compression)
    pickled = pickle.dumps(logger)
    unpickled = pickle.loads(pickled)
    unpickled.debug("A message")
    assert file.read_text() == "DEBUG - test_pickling_file_handler_compression - A message\n"


def test_pickling_no_handler(writer):
    pickled = pickle.dumps(logger)
    unpickled = pickle.loads(pickled)
    unpickled.add(writer, format="{level} - {function} - {message}")
    unpickled.debug("A message")
    assert writer.read() == "DEBUG - test_pickling_no_handler - A message\n"


def test_pickling_handler_not_serializable():
    logger.add(lambda m: None)
    with pytest.raises((pickle.PicklingError, AttributeError), match="Can't (pickle|get local)"):
        pickle.dumps(logger)


def test_pickling_filter_function(capsys):
    logger.add(print_, format="{message}", filter=filter_function)
    pickled = pickle.dumps(logger)
    unpickled = pickle.loads(pickled)
    unpickled.info("Nope")
    unpickled.info("[PASS] Yes")
    out, err = capsys.readouterr()
    assert out == "[PASS] Yes\n"
    assert err == ""


@pytest.mark.parametrize("filter", ["", "tests"])
def test_pickling_filter_name(capsys, filter):
    logger.add(print_, format="{message}", filter=filter)
    pickled = pickle.dumps(logger)
    unpickled = pickle.loads(pickled)
    unpickled.info("A message")
    out, err = capsys.readouterr()
    assert out == "A message\n"
    assert err == ""


@pytest.mark.parametrize("colorize", [True, False])
def test_pickling_format_string(capsys, colorize):
    logger.add(print_, format="-> <red>{message}</red>", colorize=colorize)
    pickled = pickle.dumps(logger)
    unpickled = pickle.loads(pickled)
    unpickled.info("The message")
    out, err = capsys.readouterr()
    assert out == parse("-> <red>The message</red>\n", strip=not colorize)
    assert err == ""


@pytest.mark.parametrize("colorize", [True, False])
def test_pickling_format_function(capsys, colorize):
    logger.add(print_, format=format_function, colorize=colorize)
    pickled = pickle.dumps(logger)
    unpickled = pickle.loads(pickled)
    unpickled.info("The message")
    out, err = capsys.readouterr()
    assert out == parse("-> <red>The message</red>", strip=not colorize)
    assert err == ""


def test_pickling_filter_function_not_serializable():
    logger.add(print, filter=lambda r: True)
    with pytest.raises((pickle.PicklingError, AttributeError), match="Can't (pickle|get local)"):
        pickle.dumps(logger)


def test_pickling_format_function_not_serializable():
    logger.add(print, format=lambda r: "{message}")
    with pytest.raises((pickle.PicklingError, AttributeError), match="Can't (pickle|get local)"):
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
    i = logger.add(print_, format="{message}")
    logger.info("A")
    pickled = pickle.dumps(logger)
    unpickled = pickle.loads(pickled)
    unpickled.remove(i)
    unpickled.info("B")
    out, err = capsys.readouterr()
    assert out == "A\n"
    assert err == ""


def test_pickling_logging_method(capsys):
    logger.add(print_, format="{level} - {function} - {message}")
    pickled = pickle.dumps(logger.critical)
    func = pickle.loads(pickled)
    func("A message")
    out, err = capsys.readouterr()
    assert out == "CRITICAL - test_pickling_logging_method - A message\n"
    assert err == ""


def test_pickling_log_method(capsys):
    logger.add(print_, format="{level} - {function} - {message}")
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
