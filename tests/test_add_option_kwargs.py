import pytest

from loguru import logger


def test_file_mode_a(tmp_path):
    file = tmp_path / "test.log"
    file.write_text("base\n")
    logger.add(file, format="{message}", mode="a")
    logger.debug("msg")
    assert file.read_text() == "base\nmsg\n"


def test_file_mode_w(tmp_path):
    file = tmp_path / "test.log"
    file.write_text("base\n")
    logger.add(file, format="{message}", mode="w")
    logger.debug("msg")
    assert file.read_text() == "msg\n"


def test_file_auto_buffering(tmp_path):
    # There doesn't seem to be a reliable way to known buffer size for text files.
    # We perform a preliminary test to ensure empirically that 128 <= buffer size <= 65536.
    dummy_filepath = tmp_path / "dummy.txt"
    with open(str(dummy_filepath), buffering=-1, mode="w") as dummy_file:
        dummy_file.write("." * 127)
        if dummy_filepath.read_text() != "":
            pytest.skip("Size buffer for text files is too small.")
        dummy_file.write("." * (65536 - 127))
        if dummy_filepath.read_text() == "":
            pytest.skip("Size buffer for text files is too big.")

    filepath = tmp_path / "test.log"
    logger.add(filepath, format="{message}", buffering=-1)
    logger.debug("A short message.")
    assert filepath.read_text() == ""
    logger.debug("A long message" + "." * 65536)
    assert filepath.read_text() != ""


def test_file_line_buffering(tmp_path):
    filepath = tmp_path / "test.log"
    logger.add(filepath, format=lambda _: "{message}", buffering=1)
    logger.debug("Without newline")
    assert filepath.read_text() == ""
    logger.debug("With newline\n")
    assert filepath.read_text() != ""


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
