import sys
import time

import pytest

from loguru import logger


class StopSinkError:
    def write(self, message):
        print(message, end="")

    def stop(self):
        raise Exception("Stop error")


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


def test_exception_in_stop_during_remove_one(capsys):
    i = logger.add(StopSinkError(), catch=False, format="{message}")
    logger.info("A")
    with pytest.raises(Exception, match=r"Stop error"):
        logger.remove(i)
    logger.info("Nope")

    out, err = capsys.readouterr()

    assert out == "A\n"
    assert err == ""


def test_exception_in_stop_not_caught_during_remove_all(capsys):
    logger.add(StopSinkError(), catch=False, format="{message}")
    logger.add(StopSinkError(), catch=False, format="{message}")

    with pytest.raises(Exception, match=r"Stop error"):
        logger.remove()

    logger.info("A")

    with pytest.raises(Exception, match=r"Stop error"):
        logger.remove()

    logger.info("Nope")

    out, err = capsys.readouterr()

    assert out == "A\n"
    assert err == ""


def test_invalid_handler_id_value(writer):
    logger.add(writer)

    with pytest.raises(ValueError, match=r"^There is no existing handler.*"):
        logger.remove(42)


@pytest.mark.parametrize("handler_id", [sys.stderr, sys, object(), int])
def test_invalid_handler_id_type(handler_id):
    with pytest.raises(TypeError, match=r"^Invalid handler id.*"):
        logger.remove(handler_id)
