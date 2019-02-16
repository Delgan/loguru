import sys
import pytest
from loguru import logger
import textwrap
import time


def test_remove_all(tmpdir, writer, capsys):
    file = tmpdir.join("test.log")

    logger.debug("This shouldn't be printed.")

    logger.add(str(file), format="{message}")
    logger.add(sys.stdout, format="{message}")
    logger.add(sys.stderr, format="{message}")
    logger.add(writer, format="{message}")

    message = "some message"
    expected = message + "\n"

    logger.debug(message)

    logger.remove()

    logger.debug("This shouldn't be printed neither.")

    out, err = capsys.readouterr()

    assert file.read() == expected
    assert out == expected
    assert err == expected
    assert writer.read() == expected


def test_remove_simple(writer):
    i = logger.add(writer, format="{message}")
    logger.debug("1")
    logger.remove(i)
    logger.debug("2")
    assert writer.read() == "1\n"


def test_remove_enqueue(writer):
    i = logger.add(writer, format="{message}", enqueue=True)
    logger.debug("1")
    time.sleep(0.1)
    logger.remove(i)
    logger.debug("2")
    assert writer.read() == "1\n"


def test_remove_enqueue_filesink(tmpdir):
    file = tmpdir.join("test.log")
    i = logger.add(str(file), format="{message}", enqueue=True)
    logger.debug("1")
    logger.remove(i)
    assert file.read() == "1\n"


def test_remove_invalid(writer):
    logger.add(writer)

    with pytest.raises(ValueError):
        logger.remove(42)
