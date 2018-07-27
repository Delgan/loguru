import sys
import pytest
from loguru import logger
import textwrap
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

def test_stop_enqueue(writer):
    i = logger.start(writer, format="{message}", enqueue=True)
    logger.debug("1")
    time.sleep(0.1)
    logger.stop(i)
    logger.debug("2")
    assert writer.read() == "1\n"

def test_stop_enqueue_filesink(tmpdir):
    i = logger.start(tmpdir.join("test.log"), format="{message}", enqueue=True)
    logger.debug("1")
    logger.stop(i)
    assert tmpdir.join("test.log").read() == "1\n"

@pytest.mark.parametrize("enqueue", [True, False])
def test_stop_atexit(pyexec, enqueue):
    code = """
    import sys
    logger.stop()
    logger.start(sys.stdout, format='{message}', enqueue=%r)
    logger.debug("!")
    """ % enqueue
    out, err = pyexec(textwrap.dedent(code), True)
    assert out == "!\n"
    assert err == ""

def test_stop_invalid(writer):
    logger.start(writer)

    with pytest.raises(ValueError):
        logger.stop(42)
