import pytest
from loguru import logger
import sys

from logging import StreamHandler, FileHandler, NullHandler


def test_stream_handler(capsys):
    logger.start(StreamHandler(sys.stderr), format="{message}")
    logger.info("test")
    logger.stop()
    logger.warning("nope")

    out, err = capsys.readouterr()
    assert out == ""
    assert err == "test\n"

def test_file_handler(tmpdir):
    file = tmpdir.join('test.log')
    logger.start(FileHandler(file), format="{message}")
    logger.info("test")
    logger.stop()
    logger.warning("nope")

    assert file.read() == "test\n"

def test_null_handler(capsys):
    logger.start(NullHandler())
    logger.error("nope")
    logger.stop()

    out, err = capsys.readouterr()
    assert out == ""
    assert err == ""
