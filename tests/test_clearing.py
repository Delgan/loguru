import sys
import pytest

message = 'some message'
expected = message + '\n'

def test_stop_all(tmpdir, writer, capsys, logger):
    file = tmpdir.join("test.log")

    logger.debug("This shouldn't be printed.")

    logger.start(file.realpath(), format='{message}')
    logger.start(sys.stdout, format='{message}')
    logger.start(sys.stderr, format='{message}')
    logger.start(writer, format='{message}')

    logger.debug(message)

    logger.stop()

    logger.debug("This shouldn't be printed neither.")

    out, err = capsys.readouterr()

    assert file.read() == expected
    assert out == expected
    assert err == expected
    assert writer.read() == expected

def test_stop_count(logger, writer):
    n = logger.stop()
    assert n == 0

    n = logger.stop(42)
    assert n == 0

    i = logger.start(writer)
    n = logger.stop(i)
    assert n == 1

    logger.start(writer)
    logger.start(writer)
    n = logger.stop()
    assert n == 2

    n = logger.stop(0)
    assert n == 0

def test_reset_handler(logger, writer):
    logger.start(writer)

    logger.reset()

    logger.debug("nope")
    assert writer.read() == ""

def test_reset_level(logger, writer):
    logger.add_level("foo", 12)

    logger.reset()

    with pytest.raises(Exception):
        logger.log("foo", "nope")

    logger.start(writer, format="{message}")
    logger.log("DEBUG", "1")
    logger.debug("2")
    assert writer.read() == "1\n2\n"

def test_reset_extra(logger, writer):
    logger.extra['a'] = 1
    logger.reset()
    assert logger.extra == {}
