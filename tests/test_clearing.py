import sys
import pytest

message = 'some message'
expected = message + '\n'

def test_clear_all(tmpdir, writer, capsys, logger):
    file = tmpdir.join("test.log")

    logger.debug("This shouldn't be printed.")

    logger.log_to(file.realpath(), format='{message}')
    logger.log_to(sys.stdout, format='{message}')
    logger.log_to(sys.stderr, format='{message}')
    logger.log_to(writer, format='{message}')

    logger.debug(message)

    logger.clear()

    logger.debug("This shouldn't be printed neither.")

    out, err = capsys.readouterr()

    assert file.read() == expected
    assert out == expected
    assert err == expected
    assert writer.read() == expected

def test_clear_count(logger, writer):
    n = logger.clear()
    assert n == 0

    n = logger.clear(42)
    assert n == 0

    i = logger.log_to(writer)
    n = logger.clear(i)
    assert n == 1

    logger.log_to(writer)
    logger.log_to(writer)
    n = logger.clear()
    assert n == 2

    n = logger.clear(0)
    assert n == 0

def test_reset_handler(logger, writer):
    logger.log_to(writer)

    logger.reset()

    logger.debug("nope")
    assert writer.read() == ""

def test_reset_level(logger, writer):
    logger.add_level("foo", 12)

    logger.reset()

    with pytest.raises(Exception):
        logger.log("foo", "nope")

    logger.log_to(writer, format="{message}")
    logger.log("DEBUG", "1")
    logger.debug("2")
    assert writer.read() == "1\n2\n"
