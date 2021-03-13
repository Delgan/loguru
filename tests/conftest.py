import asyncio
import contextlib
import logging
import os
import sys
import threading
import time
import traceback
import warnings

import pytest

import loguru

if sys.version_info < (3, 5, 3):

    def run(coro):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        res = loop.run_until_complete(coro)
        loop.close()
        asyncio.set_event_loop(None)
        return res

    asyncio.run = run
elif sys.version_info < (3, 7):

    def run(coro):
        loop = asyncio.new_event_loop()
        res = loop.run_until_complete(coro)
        loop.close()
        asyncio.set_event_loop(None)
        return res

    asyncio.run = run


def parse(text, *, strip=False, strict=True):
    parser = loguru._colorizer.AnsiParser()
    parser.feed(text)
    tokens = parser.done(strict=strict)

    if strip:
        return parser.strip(tokens)
    else:
        return parser.colorize(tokens, "")


@contextlib.contextmanager
def default_threading_excepthook():
    if not hasattr(threading, "excepthook"):
        yield
        return

    # Pytest added "PytestUnhandledThreadExceptionWarning", we need to
    # remove it temporarily for somes tests checking exceptions in threads.

    def excepthook(args):
        print("Exception in thread:", file=sys.stderr, flush=True)
        traceback.print_exception(
            args.exc_type, args.exc_value, args.exc_traceback, file=sys.stderr
        )

    old_excepthook = threading.excepthook
    threading.excepthook = excepthook
    yield
    threading.excepthook = old_excepthook


@pytest.fixture(scope="session", autouse=True)
def check_env_variables():
    for var in os.environ:
        if var.startswith("LOGURU_"):
            warnings.warn(
                "A Loguru environment variable has been detected "
                "and may interfere with the tests: '%s'" % var,
                RuntimeWarning,
            )


@pytest.fixture(autouse=True)
def reset_logger():
    def reset():
        loguru.logger.remove()
        loguru.logger.__init__(
            loguru._logger.Core(), None, 0, False, False, False, False, True, None, {}
        )
        loguru._logger.context.set({})

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

    fix_struct = os.name == "nt" and sys.version_info < (3, 6)

    def monkeypatch_date(year, month, day, hour, minute, second, microsecond, zone="UTC", offset=0):
        dt = loguru._datetime.datetime(year, month, day, hour, minute, second, microsecond)

        if fix_struct:

            class StructTime:
                def __init__(self, struct, tm_zone, tm_gmtoff):
                    self._struct = struct
                    self.tm_zone = tm_zone
                    self.tm_gmtoff = tm_gmtoff

                def __getattr__(self, name):
                    return getattr(self._struct, name)

                def __iter__(self):
                    return iter(self._struct)

            struct = StructTime(time.struct_time([*dt.timetuple()]), zone, offset)
        else:
            struct = time.struct_time([*dt.timetuple()] + [zone, offset])

        def patched_now(tz=None):
            return dt

        def patched_localtime(t):
            return struct

        monkeypatch.setattr(loguru._datetime.datetime, "now", patched_now)
        monkeypatch.setattr(loguru._datetime, "localtime", patched_localtime)

    return monkeypatch_date


@contextlib.contextmanager
def make_logging_logger(name, handler, fmt="%(message)s", level="DEBUG"):
    logging_logger = logging.getLogger(name)
    logging_logger.setLevel(level)
    formatter = logging.Formatter(fmt)

    handler.setLevel(level)
    handler.setFormatter(formatter)
    logging_logger.addHandler(handler)

    try:
        yield logging_logger
    finally:
        logging_logger.removeHandler(handler)


@pytest.fixture
def f_globals_name_absent(monkeypatch):
    getframe_ = loguru._get_frame.get_frame

    def patched_getframe(*args, **kwargs):
        frame = getframe_(*args, **kwargs)
        monkeypatch.delitem(frame.f_globals, "__name__", raising=False)
        return frame

    monkeypatch.setattr(loguru._logger, "get_frame", patched_getframe)
