import re
import sys
import time

import pytest

from loguru import logger

from .conftest import default_threading_excepthook


def broken_sink(m):
    raise ValueError("Error!")


def test_catch_is_true(capsys):
    logger.add(broken_sink, catch=True)
    logger.debug("Fail")
    out, err = capsys.readouterr()
    assert out == ""
    assert err != ""


def test_catch_is_false(capsys):
    logger.add(broken_sink, catch=False)
    with pytest.raises(ValueError, match="Error!"):
        logger.debug("Fail")
    out, err = capsys.readouterr()
    assert out == err == ""


def test_no_sys_stderr(capsys, monkeypatch):
    with monkeypatch.context() as context:
        context.setattr(sys, "stderr", None)
        logger.add(broken_sink, catch=True)
        logger.debug("a")

        out, err = capsys.readouterr()
        assert out == err == ""


def test_broken_sys_stderr(capsys, monkeypatch):
    def broken_write(*args, **kwargs):
        raise OSError

    with monkeypatch.context() as context:
        context.setattr(sys.stderr, "write", broken_write)
        logger.add(broken_sink, catch=True)
        logger.debug("a")

        out, err = capsys.readouterr()
        assert out == err == ""


def test_encoding_error(capsys):
    def sink(m):
        raise UnicodeEncodeError("utf8", "", 10, 11, "too bad")

    logger.add(sink, catch=True)
    logger.debug("test")

    out, err = capsys.readouterr()
    lines = err.strip().splitlines()

    assert out == ""
    assert lines[0] == "--- Logging error in Loguru Handler #0 ---"
    assert lines[1].startswith("Record was: {")
    assert lines[1].endswith("}")
    assert lines[-2].startswith("UnicodeEncodeError:")
    assert lines[-1] == "--- End of logging error ---"


def test_unprintable_record(writer, capsys):
    class Unprintable:
        def __repr__(self):
            raise ValueError("Failed")

    logger.add(writer, format="{message} {extra[unprintable]}", catch=True)
    logger.bind(unprintable=1).debug("a")
    logger.bind(unprintable=Unprintable()).debug("b")
    logger.bind(unprintable=2).debug("c")

    out, err = capsys.readouterr()
    lines = err.strip().splitlines()

    assert writer.read() == "a 1\nc 2\n"
    assert out == ""
    assert lines[0] == "--- Logging error in Loguru Handler #0 ---"
    assert lines[1] == "Record was: /!\\ Unprintable record /!\\"
    assert lines[-2] == "ValueError: Failed"
    assert lines[-1] == "--- End of logging error ---"


@pytest.mark.parametrize("enqueue", [False, True])
def test_broken_sink_message(capsys, enqueue):
    logger.add(broken_sink, catch=True, enqueue=enqueue)
    logger.debug("Oops")
    time.sleep(0.1)

    out, err = capsys.readouterr()
    lines = err.strip().splitlines()

    assert out == ""
    assert lines[0] == "--- Logging error in Loguru Handler #0 ---"
    assert re.match(r"Record was: \{.*Oops.*\}", lines[1])
    assert lines[-2].startswith("ValueError: Error!")
    assert lines[-1] == "--- End of logging error ---"


@pytest.mark.parametrize("enqueue", [False, True])
def test_broken_sink_caught_keep_working(enqueue):
    output = ""

    def half_broken_sink(m):
        nonlocal output
        if m.startswith("NOK"):
            raise ValueError("Broken!")
        else:
            output += m

    logger.add(half_broken_sink, format="{message}", enqueue=enqueue, catch=True)
    logger.info("A")
    logger.info("NOK")
    logger.info("B")

    time.sleep(0.1)
    assert output == "A\nB\n"


def test_broken_sink_not_caught_enqueue():
    called = 0

    def broken_sink(m):
        nonlocal called
        called += 1
        raise ValueError("Nop")

    logger.add(broken_sink, format="{message}", enqueue=True, catch=False)

    with default_threading_excepthook():
        logger.info("A")
        logger.info("B")
        time.sleep(0.1)

    assert called == 2
