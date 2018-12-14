import pathlib
import sys
import os
import logging
from loguru import logger
import pytest


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
    path = file.realpath()
    sink = sink_from_path(path)
    log(sink, rep)
    assert file.read() == expected * rep


@repetitions
def test_file_sink_folder_creation(rep, tmpdir):
    file = tmpdir.join("some", "sub", "folder", "not", "existing", "test.log")
    log(file.realpath(), rep)
    assert file.read() == expected * rep


@repetitions
def test_function_sink(rep):
    a = []
    func = lambda log_message: a.append(log_message)
    log(func, rep)
    assert a == [expected] * rep


@repetitions
def test_class_sink(rep):
    out = []

    class A:
        def write(self, m):
            out.append(m)

    log(A, rep)
    assert out == [expected] * rep


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

    log(A, rep)
    assert flushed == [expected] * rep


@pytest.mark.parametrize("sink", [123, sys, object(), int])
def test_invalid_sink(sink):
    with pytest.raises(ValueError):
        log(sink, "")


def test_deprecated_start_and_stop(writer):
    i = logger.start(writer, format="{message}")
    logger.debug("Test")
    assert writer.read() == "Test\n"
    writer.clear()
    logger.stop(i)
    logger.debug("Test")
    assert writer.read() == ""
