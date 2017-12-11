import loguru
import logging
import itertools
import pytest
import py
import os

default_levels = loguru._logger.Logger._levels.copy()

@pytest.fixture(autouse=True)
def reset_logger():
    yield
    loguru._logger.Logger._levels = default_levels.copy()
    loguru._logger.Logger._min_level = float('inf')
    loguru._logger.Logger._handlers_simple = {}
    loguru._logger.Logger._handlers_queued = {}
    loguru._logger.Logger._handlers_count = itertools.count()
    loguru._logger.Logger._enabled = {}
    loguru._logger.Logger._activation_list = []
    loguru._logger.Logger._queue = None
    loguru._logger.Logger._thread = None
    loguru.logger.extra = {}

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
    logger_handler = None
    logger_level = None

    def make_logging_logger(name, handler, fmt="%(message)s", level="DEBUG"):
        nonlocal logger_handler, logging_logger, logger_level
        logging_logger = logging.getLogger(name)
        logger_level = logging_logger.getEffectiveLevel()
        logging_logger.setLevel(level)
        logger_handler = handler
        formatter = logging.Formatter(fmt)

        logger_handler.setLevel(level)
        logger_handler.setFormatter(formatter)
        logging_logger.addHandler(logger_handler)

        return logging_logger

    yield make_logging_logger

    if logging_logger:
        logging_logger.setLevel(logger_level)
        logging_logger.removeHandler(logger_handler)

