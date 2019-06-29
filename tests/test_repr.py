from loguru import logger
import logging
import sys
import pathlib
import re

def test_no_handler():
    assert repr(logger) == "<loguru.logger handlers=[]>"


def test_stderr():
    logger.add(sys.__stderr__)
    assert repr(logger) == "<loguru.logger handlers=[(id=0, level=10, writer=<stderr>)]>"


def test_stdout():
    logger.add(sys.__stdout__)
    assert repr(logger) == "<loguru.logger handlers=[(id=0, level=10, writer=<stdout>)]>"


def test_file_object(tmpdir):
    path = str(tmpdir.join("test.log"))
    file = open(path, "w")
    logger.add(file)
    assert repr(logger) == "<loguru.logger handlers=[(id=0, level=10, writer=%s)]>" % path


def test_file_str(tmpdir):
    path = str(tmpdir.join("test.log"))
    logger.add(path)
    assert repr(logger) == "<loguru.logger handlers=[(id=0, level=10, writer=%s)]>" % path


def test_file_pathlib(tmpdir):
    path = str(tmpdir.join("test.log"))
    logger.add(pathlib.Path(path))
    assert repr(logger) == "<loguru.logger handlers=[(id=0, level=10, writer=%s)]>" % path


def test_stream_object():
    class MyStream:
        def __init__(self, name):
            self.name = name

        def write(self, m):
            pass

        def __repr__(self):
            return "MyStream()"

    logger.add(MyStream("<foobar>"))
    assert repr(logger) == "<loguru.logger handlers=[(id=0, level=10, writer=<foobar>)]>"


def test_stream_object_without_name_attr():
    class MyStream:
        def write(self, m):
            pass

        def __repr__(self):
            return "MyStream()"

    logger.add(MyStream())
    assert repr(logger) == "<loguru.logger handlers=[(id=0, level=10, writer=MyStream())]>"


def test_class():
    class MyStream:
        def __init__(self):
            self.name = "<foobar>"

        def write(self, m):
            pass

        def __repr__(self):
            return "MyStream()"

    logger.add(MyStream)
    assert repr(logger) == "<loguru.logger handlers=[(id=0, level=10, writer=<foobar>)]>"


def test_class_without_name_attr():
    class MyStream:
        def write(self, m):
            pass

        def __repr__(self):
            return "MyStream()"

    logger.add(MyStream)
    assert repr(logger) == "<loguru.logger handlers=[(id=0, level=10, writer=MyStream())]>"


def test_function():
    def my_function(message):
        pass

    logger.add(my_function)
    assert repr(logger) == "<loguru.logger handlers=[(id=0, level=10, writer=my_function)]>"


def test_function_without_name():
    class Function:
        def __call__(self, message):
            pass

        def __repr__(self):
            return "<Function>"

        def __getattr__(self, name):
            if name == "__name__":
                raise AttributeError
            return getattr(self.__class__, name)

    function = Function()
    logger.add(function)
    assert repr(logger) == "<loguru.logger handlers=[(id=0, level=10, writer=<Function>)]>"


def test_standard_handler():
    handler = logging.StreamHandler(sys.__stderr__)
    logger.add(handler)
    if sys.version_info >= (3, 6):
        r = "<loguru.logger handlers=[(id=0, level=10, writer=<StreamHandler <stderr> (NOTSET)>)]>"
        assert repr(logger) == r
    else:
        r = r"<loguru\.logger handlers=\[\(id=0, level=10, writer=<logging\.StreamHandler .*>\)\]>"
        assert re.match(r, repr(logger))


def test_standard_handler_class():
    handler = logging.Handler
    logger.add(handler)
    if sys.version_info >= (3, 6):
        r = "<loguru.logger handlers=[(id=0, level=10, writer=<Handler (NOTSET)>)]>"
        assert repr(logger) == r
    else:
        r = r"<loguru\.logger handlers=\[\(id=0, level=10, writer=<logging\.Handler .*>\)\]>"
        assert re.match(r, repr(logger))

def test_multiple_handlers():
    logger.add(sys.__stdout__)
    logger.add(sys.__stderr__)
    r = "<loguru.logger handlers=[(id=0, level=10, writer=<stdout>), (id=1, level=10, writer=<stderr>)]>"
    assert repr(logger) == r


def test_handler_removed():
    i = logger.add(sys.__stdout__)
    logger.add(sys.__stderr__)
    logger.remove(i)
    assert repr(logger) == "<loguru.logger handlers=[(id=1, level=10, writer=<stderr>)]>"


def test_handler_level_name():
    logger.add(sys.__stderr__, level="TRACE")
    assert repr(logger) == "<loguru.logger handlers=[(id=0, level=5, writer=<stderr>)]>"


def test_handler_level_num():
    logger.add(sys.__stderr__, level=33)
    assert repr(logger) == "<loguru.logger handlers=[(id=0, level=33, writer=<stderr>)]>"
