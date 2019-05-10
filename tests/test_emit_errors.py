import sys
import pytest
from loguru import logger
import loguru
import time


def broken_sink(m):
    raise Exception("Error!")


def test_no_sys_stderr(capsys, monkeypatch):
    monkeypatch.setattr(sys, "stderr", None)
    logger.add(broken_sink)
    logger.debug("a")

    out, err = capsys.readouterr()
    assert out == err == ""


def test_broken_sys_stderr(capsys, monkeypatch):
    def broken_write(*args, **kwargs):
        raise OSError

    monkeypatch.setattr(sys.stderr, "write", broken_write)
    logger.add(broken_sink)
    logger.debug("a")

    out, err = capsys.readouterr()
    assert out == err == ""


def test_encoding_error(capsys):
    def sink(m):
        raise UnicodeEncodeError("utf8", "", 10, 11, "too bad")

    logger.add(sink)
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

    logger.add(writer, format="{message} {extra[unprintable]}")
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
def test_broken_sink(capsys, enqueue):
    logger.add(broken_sink, catch=True, enqueue=enqueue)
    logger.debug("Oops")
    time.sleep(0.1)

    out, err = capsys.readouterr()
    lines = err.strip().splitlines()

    assert out == ""
    assert lines[0] == "--- Logging error in Loguru Handler #0 ---"
    assert lines[1].startswith("Record was: {")
    assert lines[1].endswith("}")
    assert lines[-2].startswith("Exception: Error!")
    assert lines[-1] == "--- End of logging error ---"
