import loguru
import logging
import itertools
import pytest
import py
import os

default_levels = loguru._logger.Logger._levels.copy()

def reset_logger():
    loguru._logger.Logger._levels.clear()
    loguru._logger.Logger._levels.update(default_levels)
    loguru._logger.Logger._min_level = float('inf')
    loguru._logger.Logger._handlers.clear()
    loguru._logger.Logger._handlers_count = itertools.count()
    loguru._logger.Logger._enabled.clear()
    loguru._logger.Logger._activation_list.clear()
    loguru._logger.Logger._propagated = None

@pytest.fixture
def logger():
    reset_logger()
    yield loguru._logger.Logger()
    reset_logger()

@pytest.fixture
def writer():

    def w(message):
        w.written.append(message)

    w.written = []
    w.read = lambda: ''.join(w.written)
    w.clear = lambda: w.written.clear()

    return w

@pytest.fixture
def pyexec(tmpdir):
    file = tmpdir.join("test.py")
    loguru_path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    loguru_config = ('import sys;'
                     'sys.path.append("' + loguru_path + '");'
                     'from loguru import logger;'
                     'logger.stop();\n')

    def pyexec(code, import_loguru=False, *, pyfile=None):
        if import_loguru:
            code = loguru_config + code
        else:
            code = "# padding\n" + code

        if pyfile is None:
            pyfile = file
        pyfile.write(code)
        out = py.process.cmdexec('python %s' % pyfile.realpath())
        return out

    return pyexec

@pytest.fixture
def monkeypatch_now(monkeypatch):

    def monkeypatch_now(func):
        monkeypatch.setattr(loguru._logger, 'pendulum_now', func)
        monkeypatch.setattr(loguru._file_sink, 'pendulum_now', func)

    return monkeypatch_now

@pytest.fixture
def make_logging_logger():

    logging_logger = None
    handler = None

    def make_logging_logger(name, stream, fmt="%(message)s", level="DEBUG"):
        nonlocal handler, logging_logger
        logging_logger = logging.getLogger(name)
        logging_logger.setLevel(level)
        handler = logging.StreamHandler(stream)
        formatter = logging.Formatter(fmt)

        handler.setLevel(level)
        handler.setFormatter(formatter)
        logging_logger.addHandler(handler)

        return logging_logger

    yield make_logging_logger

    logging_logger.setLevel("NOTSET")
    logging_logger.removeHandler(handler)

