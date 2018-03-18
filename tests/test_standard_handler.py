import pytest
from loguru import logger
import sys
from tempfile import TemporaryDirectory

from logging import StreamHandler, FileHandler, NullHandler, LogRecord


def make_handler(klass):

    class SuperHandler(klass):
        terminator = ''

        def write(self, message):
            r = message.record
            record = LogRecord(r['name'], r['level'], r['file'].path, r['line'],
                               message, [], r['exception'], r['function'])
            self.emit(record)

    return SuperHandler

def test_stream_handler(capsys):
    handler = make_handler(StreamHandler)(sys.stderr)

    logger.start(handler, format="{message}")
    logger.info("test")
    logger.stop()
    logger.warning("nope")

    out, err = capsys.readouterr()
    assert out == ""
    assert err == "test\n"

def test_file_handler(tmpdir):
    file = tmpdir.join('test.log')
    handler = make_handler(FileHandler)(file)
    logger.start(handler, format="{message}")
    logger.info("test")
    logger.stop()
    logger.warning("nope")

    assert file.read() == "test\n"

def test_null_handler(capsys):
    handler = make_handler(NullHandler)()
    logger.start(handler)
    logger.error("nope")
    logger.stop()

    out, err = capsys.readouterr()
    assert out == ""
    assert err == ""
