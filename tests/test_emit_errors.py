import sys
from loguru import logger
import loguru
import time


def broken_sink(m):
    raise Exception


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
    assert lines[0] == "--- Logging error in Loguru ---"
    assert lines[1].startswith("Record was: {")
    assert lines[1].endswith("}")
    assert (
        lines[-2]
        == "UnicodeEncodeError: 'utf8' codec can't encode characters in position 10-10: too bad"
    )
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

    assert out == ""
    assert lines[0] == "--- Logging error in Loguru ---"
    assert lines[1] == "Record was: /!\\ Unprintable record /!\\"
    assert lines[-2] == "ValueError: Failed"
    assert lines[-1] == "--- End of logging error ---"
    assert writer.read() == "a 1\nc 2\n"


def test_enqueue_broken_sink(monkeypatch):
    out = []
    monkeypatch.setattr(
        loguru._handler.Handler, "handle_error", lambda *args: out.append("Handled")
    )
    logger.add(broken_sink, enqueue=True)
    logger.debug("a")
    time.sleep(0.1)
    assert out[0] == "Handled"
