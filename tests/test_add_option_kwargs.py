import io

import pytest

from loguru import logger


def test_file_mode_a(tmpdir):
    file = tmpdir.join("test.log")
    file.write("base\n")
    logger.add(str(file), format="{message}", mode="a")
    logger.debug("msg")
    assert file.read() == "base\nmsg\n"


def test_file_mode_w(tmpdir):
    file = tmpdir.join("test.log")
    file.write("base\n")
    logger.add(str(file), format="{message}", mode="w")
    logger.debug("msg")
    assert file.read() == "msg\n"


def test_file_buffering(tmpdir):
    file = tmpdir.join("test.log")
    logger.add(str(file), format="{message}", buffering=-1)
    logger.debug("x" * (io.DEFAULT_BUFFER_SIZE // 2))
    assert file.read() == ""
    logger.debug("x" * (io.DEFAULT_BUFFER_SIZE * 2))
    assert file.read() != ""


def test_invalid_function_kwargs():
    def function(message):
        pass

    with pytest.raises(TypeError, match=r"add\(\) got an unexpected keyword argument"):
        logger.add(function, b="X")


def test_invalid_file_object_kwargs():
    class Writer:
        def __init__(self):
            self.out = ""

        def write(self, m):
            pass

    writer = Writer()

    with pytest.raises(TypeError, match=r"add\(\) got an unexpected keyword argument"):
        logger.add(writer, format="{message}", kw1="1", kw2="2")


def test_invalid_file_kwargs():
    with pytest.raises(TypeError, match=r".*keyword argument;*"):
        logger.add("file.log", nope=123)


def test_invalid_coroutine_kwargs():
    async def foo():
        pass

    with pytest.raises(TypeError, match=r"add\(\) got an unexpected keyword argument"):
        logger.add(foo, nope=123)
