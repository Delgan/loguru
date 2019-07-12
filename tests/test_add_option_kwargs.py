import pytest
from loguru import logger
import io


def test_function_with_kwargs():
    out = []

    def function(message, kw2, kw1):
        out.append(message + kw1 + "a" + kw2)

    logger.add(function, format="{message}", kw1="1", kw2="2")
    logger.debug("msg")
    assert out == ["msg\n1a2"]


def test_class_with_kwargs():
    out = []

    class Writer:
        def __init__(self, kw2, kw1):
            self.end = kw1 + "b" + kw2

        def write(self, m):
            out.append(m + self.end)

    logger.add(Writer, format="{message}", kw1="1", kw2="2")
    logger.debug("msg")
    assert out == ["msg\n1b2"]


def test_file_object_with_kwargs():
    class Writer:
        def __init__(self):
            self.out = ""

        def write(self, m, kw2, kw1):
            self.out += m + kw1 + "c" + kw2

    writer = Writer()
    logger.add(writer, format="{message}", kw1="1", kw2="2")
    logger.debug("msg")
    assert writer.out == "msg\n1c2"


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
    def function(message, a="Y"):
        pass

    logger.add(function, b="X", catch=False)
    with pytest.raises(TypeError):
        logger.debug("Nope")


def test_invalid_class_kwargs():
    class Writer:
        pass

    with pytest.raises(TypeError):
        logger.add(Writer, keyword=123)


def test_invalid_file_object_kwargs():
    class Writer:
        def __init__(self):
            self.out = ""

        def write(self, m):
            pass

    writer = Writer()
    logger.add(writer, format="{message}", kw1="1", kw2="2", catch=False)
    with pytest.raises(TypeError):
        logger.debug("msg")


def test_invalid_file_kwargs():
    with pytest.raises(TypeError):
        logger.add("file.log", nope=123)
