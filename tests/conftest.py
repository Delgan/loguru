import loguru
import logging
import itertools
import pytest
import os
import subprocess
import time

default_levels = loguru._logger.Logger._levels.copy()


@pytest.fixture(autouse=True)
def reset_logger():
    def reset():
        loguru.logger.remove()
        loguru.logger.__init__({}, None, False, False, False, False, 0)
        loguru._logger.Logger._levels = default_levels.copy()
        loguru._logger.Logger._min_level = float("inf")
        loguru._logger.Logger._extra_class = {}
        loguru._logger.Logger._handlers = {}
        loguru._logger.Logger._handlers_count = itertools.count()
        loguru._logger.Logger._enabled = {}
        loguru._logger.Logger._activation_list = []
        logging.Logger.manager.loggerDict.clear()
        logging.root = logging.RootLogger(logging.WARNING)

    reset()
    yield
    reset()


@pytest.fixture
def writer():
    def w(message):
        w.written.append(message)

    w.written = []
    w.read = lambda: "".join(w.written)
    w.clear = lambda: w.written.clear()

    return w


@pytest.fixture
def sink_with_logger():
    class SinkWithLogger:
        def __init__(self, logger):
            self.logger = logger
            self.out = ""

        def write(self, message):
            self.logger.info(message)
            self.out += message

    return SinkWithLogger


@pytest.fixture
def monkeypatch_date(monkeypatch):
    def monkeypatch_date(year, month, day, hour, minute, second, microsecond, zone="UTC", offset=0):
        dt = loguru._datetime.datetime(year, month, day, hour, minute, second, microsecond)
        struct = time.struct_time([*dt.timetuple()] + [zone, offset])

        def patched_now(tz=None):
            return dt

        def patched_localtime(t):
            return struct

        monkeypatch.setattr(loguru._datetime.datetime, "now", patched_now)
        monkeypatch.setattr(loguru._datetime, "localtime", patched_localtime)

    return monkeypatch_date


@pytest.fixture
def make_logging_logger():
    def make_logging_logger(name, handler, fmt="%(message)s", level="DEBUG"):
        logging_logger = logging.getLogger(name)
        logging_logger.setLevel(level)
        formatter = logging.Formatter(fmt)

        handler.setLevel(level)
        handler.setFormatter(formatter)
        logging_logger.addHandler(handler)

        return logging_logger

    yield make_logging_logger
