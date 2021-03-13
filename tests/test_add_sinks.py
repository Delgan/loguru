import asyncio
import logging
import os
import pathlib
import sys

import pytest

from loguru import logger

message = "test message"
expected = message + "\n"

repetitions = pytest.mark.parametrize("rep", [0, 1, 2])


def log(sink, rep=1):
    logger.debug("This shouldn't be printed.")
    i = logger.add(sink, format="{message}")
    for _ in range(rep):
        logger.debug(message)
    logger.remove(i)
    logger.debug("This shouldn't be printed neither.")


async def async_log(sink, rep=1):
    logger.debug("This shouldn't be printed.")
    i = logger.add(sink, format="{message}")
    for _ in range(rep):
        logger.debug(message)
    await logger.complete()
    logger.remove(i)
    logger.debug("This shouldn't be printed neither.")


@repetitions
def test_stdout_sink(rep, capsys):
    log(sys.stdout, rep)
    out, err = capsys.readouterr()
    assert out == expected * rep
    assert err == ""


@repetitions
def test_stderr_sink(rep, capsys):
    log(sys.stderr, rep)
    out, err = capsys.readouterr()
    assert out == ""
    assert err == expected * rep


@repetitions
def test_devnull(rep):
    log(os.devnull, rep)


@repetitions
@pytest.mark.parametrize(
    "sink_from_path",
    [str, pathlib.Path, lambda path: open(path, "a"), lambda path: pathlib.Path(path).open("a")],
)
def test_file_sink(rep, sink_from_path, tmpdir):
    file = tmpdir.join("test.log")
    sink = sink_from_path(str(file))
    log(sink, rep)
    assert file.read() == expected * rep


@repetitions
def test_file_sink_folder_creation(rep, tmpdir):
    file = tmpdir.join("some", "sub", "folder", "not", "existing", "test.log")
    log(str(file), rep)
    assert file.read() == expected * rep


@repetitions
def test_function_sink(rep):
    a = []

    def func(log_message):
        a.append(log_message)

    log(func, rep)
    assert a == [expected] * rep


@repetitions
def test_coroutine_sink(capsys, rep):
    async def async_print(msg):
        await asyncio.sleep(0.01)
        print(msg, end="")
        await asyncio.sleep(0.01)

    asyncio.run(async_log(async_print, rep))

    out, err = capsys.readouterr()
    assert err == ""
    assert out == expected * rep


@repetitions
def test_file_object_sink(rep):
    class A:
        def __init__(self):
            self.out = ""

        def write(self, m):
            self.out += m

    a = A()
    log(a, rep)
    assert a.out == expected * rep


@repetitions
def test_standard_handler_sink(rep):
    out = []

    class H(logging.Handler):
        def emit(self, record):
            out.append(record.getMessage() + "\n")

    h = H()
    log(h, rep)
    assert out == [expected] * rep


@repetitions
def test_flush(rep):
    flushed = []
    out = []

    class A:
        def write(self, m):
            out.append(m)

        def flush(self):
            flushed.append(out[-1])

    log(A(), rep)
    assert flushed == [expected] * rep


def test_file_sink_ascii_encoding(tmpdir):
    file = tmpdir.join("test.log")
    logger.add(
        str(file), encoding="ascii", format="{message}", errors="backslashreplace", catch=False
    )
    logger.info("天")
    logger.remove()
    assert file.read_text("ascii") == "\\u5929\n"


def test_file_sink_utf8_encoding(tmpdir):
    file = tmpdir.join("test.log")
    logger.add(str(file), encoding="utf8", format="{message}", errors="strict", catch=False)
    logger.info("天")
    logger.remove()
    assert file.read_text("utf8") == "天\n"


def test_disabled_logger_in_sink(sink_with_logger):
    sink = sink_with_logger(logger)
    logger.disable("tests.conftest")
    logger.add(sink, format="{message}")
    logger.info("Disabled test")
    assert sink.out == "Disabled test\n"


@pytest.mark.parametrize("flush", [123, None])
def test_custom_sink_invalid_flush(capsys, flush):
    class Sink:
        def __init__(self):
            self.flush = flush

        def write(self, message):
            print(message, end="")

    logger.add(Sink(), format="{message}")
    logger.info("Test")

    out, err = capsys.readouterr()
    assert out == "Test\n"
    assert err == ""


@pytest.mark.parametrize("stop", [123, None])
def test_custom_sink_invalid_stop(capsys, stop):
    class Sink:
        def __init__(self):
            self.stop = stop

        def write(self, message):
            print(message, end="")

    logger.add(Sink(), format="{message}")
    logger.info("Test")
    logger.remove()

    out, err = capsys.readouterr()
    assert out == "Test\n"
    assert err == ""


@pytest.mark.parametrize("complete", [123, None, lambda: None])
def test_custom_sink_invalid_complete(capsys, complete):
    class Sink:
        def __init__(self):
            self.complete = complete

        def write(self, message):
            print(message, end="")

    async def worker():
        logger.info("Test")
        await logger.complete()

    logger.add(Sink(), format="{message}")
    asyncio.run(worker())

    out, err = capsys.readouterr()
    assert out == "Test\n"
    assert err == ""


@pytest.mark.parametrize("sink", [123, sys, object(), int])
def test_invalid_sink(sink):
    with pytest.raises(TypeError):
        log(sink, "")


def test_deprecated_start_and_stop(writer):
    with pytest.warns(DeprecationWarning):
        i = logger.start(writer, format="{message}")
    logger.debug("Test")
    assert writer.read() == "Test\n"
    writer.clear()
    with pytest.warns(DeprecationWarning):
        logger.stop(i)
    logger.debug("Test")
    assert writer.read() == ""
