import pytest
from loguru import logger
import sys

from logging import StreamHandler, FileHandler, NullHandler, Handler
from logging import Formatter


def test_stream_handler(capsys):
    logger.add(StreamHandler(sys.stderr), format="{level} {message}")
    logger.info("test")
    logger.remove()
    logger.warning("nope")

    out, err = capsys.readouterr()
    assert out == ""
    assert err == "INFO test\n"


def test_file_handler(tmpdir):
    file = tmpdir.join("test.log")
    logger.add(FileHandler(str(file)), format="{message} {level.name}")
    logger.info("test")
    logger.remove()
    logger.warning("nope")

    assert file.read() == "test INFO\n"


def test_null_handler(capsys):
    logger.add(NullHandler())
    logger.error("nope")
    logger.remove()

    out, err = capsys.readouterr()
    assert out == ""
    assert err == ""


def test_no_exception():
    result = None

    class NoExceptionHandler(Handler):
        def emit(self, record):
            nonlocal result
            result = bool(not record.exc_info)

    logger.add(NoExceptionHandler())

    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("Error")

    assert result is False


def test_exception(capsys):
    result = None

    class ExceptionHandler(Handler):
        def emit(self, record):
            nonlocal result
            result = bool(record.exc_info)

    logger.add(ExceptionHandler())

    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("Error")

    assert result is True


def test_exception_formatting(tmpdir):
    file = tmpdir.join("test.log")
    logger.add(FileHandler(str(file)), format="{message}")

    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("Error")

    result = file.read()
    lines = result.strip().splitlines()

    error = "ZeroDivisionError: division by zero"

    assert lines[1].startswith("Traceback")
    assert lines[-1] == error
    assert result.count(error) == 1


@pytest.mark.parametrize("dynamic_format", [False, True])
def test_standard_formatter(capsys, dynamic_format):
    fmt = "{level.no} {message} [Not Chopped]"
    if dynamic_format:
        def format_(x): return fmt
    else:
        format_ = fmt
    handler = StreamHandler(sys.stdout)
    formatter = Formatter("%(message)s %(levelname)s")
    handler.setFormatter(formatter)
    logger.add(handler, format=format_)
    logger.info("Test")
    out, err = capsys.readouterr()
    assert out == "20 Test [Not Chopped] INFO\n"
    assert err == ""


@pytest.mark.parametrize("dynamic_format", [False, True])
def test_standard_formatter_with_new_line(capsys, dynamic_format):
    fmt = "{level.no} {message}\n"
    if dynamic_format:
        def format_(x): return fmt
    else:
        format_ = fmt
    handler = StreamHandler(sys.stdout)
    formatter = Formatter("%(message)s %(levelname)s")
    handler.setFormatter(formatter)
    logger.add(handler, format=format_)
    logger.info("Test")
    out, err = capsys.readouterr()
    assert out == "20 Test\n INFO\n"
    assert err == ""


@pytest.mark.parametrize("dynamic_format", [False, True])
def test_raw_standard_formatter(capsys, dynamic_format):
    fmt = "{level.no} {message} [Not Chopped]"
    if dynamic_format:
        def format_(x): return fmt
    else:
        format_ = fmt
    handler = StreamHandler(sys.stdout)
    formatter = Formatter("%(message)s %(levelname)s")
    handler.setFormatter(formatter)
    logger.add(handler, format=format_)
    logger.opt(raw=True).info("Test")
    out, err = capsys.readouterr()
    assert out == "Test INFO\n"
    assert err == ""


@pytest.mark.parametrize("dynamic_format", [False, True])
def test_raw_standard_formatter_with_new_line(capsys, dynamic_format):
    fmt = "{level.no} {message}\n"
    if dynamic_format:
        def format_(x): return fmt
    else:
        format_ = fmt
    handler = StreamHandler(sys.stdout)
    formatter = Formatter("%(message)s %(levelname)s")
    handler.setFormatter(formatter)
    logger.add(handler, format=format_)
    logger.opt(raw=True).info("Test")
    out, err = capsys.readouterr()
    assert out == "Test INFO\n"
    assert err == ""
