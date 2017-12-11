import sys
import pytest
from loguru import logger
import time

def test_stop_all(tmpdir, writer, capsys):
    file = tmpdir.join("test.log")

    logger.debug("This shouldn't be printed.")

    logger.start(file.realpath(), format='{message}')
    logger.start(sys.stdout, format='{message}')
    logger.start(sys.stderr, format='{message}')
    logger.start(writer, format='{message}')

    message = 'some message'
    expected = message + '\n'

    logger.debug(message)

    logger.stop()

    logger.debug("This shouldn't be printed neither.")

    out, err = capsys.readouterr()

    assert file.read() == expected
    assert out == expected
    assert err == expected
    assert writer.read() == expected

def test_stop_simple(writer):
    i = logger.start(writer, format="{message}")
    logger.debug("1")
    logger.stop(i)
    logger.debug("2")
    assert writer.read() == "1\n"

def test_stop_queued(writer):
    i = logger.start(writer, format="{message}", queued=True)
    logger.debug("1")
    time.sleep(0.1)
    logger.stop(i)
    logger.debug("2")
    assert writer.read() == "1\n"

def test_stop_invalid(writer):
    logger.start(writer)

    with pytest.raises(ValueError):
        logger.stop(42)
