import logging
import pathlib
import re
import sys

from loguru import logger


def test_no_handler():
    assert repr(logger) == "<loguru.logger handlers=[]>"


def test_stderr():
    logger.add(sys.__stderr__)
    assert repr(logger) == "<loguru.logger handlers=[(id=0, level=10, sink=<stderr>)]>"


def test_stdout():
    logger.add(sys.__stdout__)
    assert repr(logger) == "<loguru.logger handlers=[(id=0, level=10, sink=<stdout>)]>"


def test_file_object(tmp_path):
    path = str(tmp_path / "test.log")
    file = open(path, "w")
    logger.add(file)
    assert repr(logger) == "<loguru.logger handlers=[(id=0, level=10, sink=%s)]>" % path


def test_file_str(tmp_path):
    path = str(tmp_path / "test.log")
    logger.add(path)
    assert repr(logger) == "<loguru.logger handlers=[(id=0, level=10, sink='%s')]>" % path


def test_file_pathlib(tmp_path):
    path = str(tmp_path / "test.log")
    logger.add(pathlib.Path(path))
    assert repr(logger) == "<loguru.logger handlers=[(id=0, level=10, sink='%s')]>" % path


def test_stream_object():
    class MyStream:
        def __init__(self, name):
            self.name = name

        def write(self, m):
            pass

        def __repr__(self):
            return "MyStream()"

    logger.add(MyStream("<foobar>"))
    assert repr(logger) == "<loguru.logger handlers=[(id=0, level=10, sink=<foobar>)]>"


def test_stream_object_without_name_attr():
    class MyStream:
        def write(self, m):
            pass

        def __repr__(self):
            return "MyStream()"

    logger.add(MyStream())
    assert repr(logger) == "<loguru.logger handlers=[(id=0, level=10, sink=MyStream())]>"


def test_stream_object_with_empty_name():
    class MyStream2:
        def __init__(self):
            self.name = ""

        def write(self, message):
            pass

        def __repr__(self):
            return "MyStream2()"

    logger.add(MyStream2())
    assert repr(logger) == "<loguru.logger handlers=[(id=0, level=10, sink=MyStream2())]>"


def test_function():
    def my_function(message):
        pass

    logger.add(my_function)
    assert repr(logger) == "<loguru.logger handlers=[(id=0, level=10, sink=my_function)]>"


def test_callable_without_name():
    class Function:
        def __call__(self):
            pass

        def __repr__(self):
            return "<FunctionWithout>"

    logger.add(Function())
    assert repr(logger) == "<loguru.logger handlers=[(id=0, level=10, sink=<FunctionWithout>)]>"


def test_callable_with_empty_name():
    class Function:
        __name__ = ""

        def __call__(self):
            pass

        def __repr__(self):
            return "<FunctionEmpty>"

    logger.add(Function())
    assert repr(logger) == "<loguru.logger handlers=[(id=0, level=10, sink=<FunctionEmpty>)]>"


def test_coroutine_function():
    async def my_async_function(message):
        pass

    logger.add(my_async_function)
    assert repr(logger) == "<loguru.logger handlers=[(id=0, level=10, sink=my_async_function)]>"


def test_coroutine_callable_without_name():
    class CoroutineFunction:
        async def __call__(self):
            pass

        def __repr__(self):
            return "<AsyncFunctionWithout>"

    logger.add(CoroutineFunction())
    assert (
        repr(logger) == "<loguru.logger handlers=[(id=0, level=10, sink=<AsyncFunctionWithout>)]>"
    )


def test_coroutine_function_with_empty_name():
    class CoroutineFunction:
        __name__ = ""

        def __call__(self):
            pass

        def __repr__(self):
            return "<AsyncFunctionEmpty>"

    logger.add(CoroutineFunction())
    assert repr(logger) == "<loguru.logger handlers=[(id=0, level=10, sink=<AsyncFunctionEmpty>)]>"


def test_standard_handler():
    handler = logging.StreamHandler(sys.__stderr__)
    logger.add(handler)
    if sys.version_info >= (3, 6):
        r = "<loguru.logger handlers=[(id=0, level=10, sink=<StreamHandler <stderr> (NOTSET)>)]>"
        assert repr(logger) == r
    else:
        r = r"<loguru\.logger handlers=\[\(id=0, level=10, sink=<logging\.StreamHandler .*>\)\]>"
        assert re.match(r, repr(logger))


def test_multiple_handlers():
    logger.add(sys.__stdout__)
    logger.add(sys.__stderr__)
    r = (
        "<loguru.logger handlers=["
        "(id=0, level=10, sink=<stdout>), "
        "(id=1, level=10, sink=<stderr>)"
        "]>"
    )
    assert repr(logger) == r


def test_handler_removed():
    i = logger.add(sys.__stdout__)
    logger.add(sys.__stderr__)
    logger.remove(i)
    assert repr(logger) == "<loguru.logger handlers=[(id=1, level=10, sink=<stderr>)]>"


def test_handler_level_name():
    logger.add(sys.__stderr__, level="TRACE")
    assert repr(logger) == "<loguru.logger handlers=[(id=0, level=5, sink=<stderr>)]>"


def test_handler_level_num():
    logger.add(sys.__stderr__, level=33)
    assert repr(logger) == "<loguru.logger handlers=[(id=0, level=33, sink=<stderr>)]>"
