import asyncio
import builtins
import contextlib
import datetime
import logging
import os
import pathlib
import sys
import threading
import time
import traceback
import warnings
from collections import namedtuple

import freezegun
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

if sys.version_info < (3, 6):

    @pytest.fixture
    def tmp_path(tmp_path):
        yield pathlib.Path(str(tmp_path))


if sys.version_info >= (3, 6):

    def pytest_configure(config):
        assert hasattr(config.option, "mypy_ini_file")
        dirname = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config.option.mypy_ini_file = os.path.join(dirname, "tox.ini")


def parse(text, *, strip=False, strict=True):
    parser = loguru._colorizer.AnsiParser()
    parser.feed(text)
    tokens = parser.done(strict=strict)

    if strip:
        return parser.strip(tokens)
    else:
        return parser.colorize(tokens, "")


def check_dir(dir, *, files=None, size=None):
    actual_files = set(dir.iterdir())
    seen = set()
    if size is not None:
        assert len(actual_files) == size
    if files is not None:
        assert len(actual_files) == len(files)
        for name, content in files:
            filepath = dir / name
            assert filepath in actual_files
            assert filepath not in seen
            if content is not None:
                assert filepath.read_text() == content
            seen.add(filepath)


@contextlib.contextmanager
def default_threading_excepthook():
    if not hasattr(threading, "excepthook"):
        yield
        return

    # Pytest added "PytestUnhandledThreadExceptionWarning", we need to
    # remove it temporarily for some tests checking exceptions in threads.

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
            loguru._logger.Core(), None, 0, False, False, False, False, True, [], {}
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
def freeze_time(monkeypatch):
    @contextlib.contextmanager
    def freeze_time(date, timezone=("UTC", 0), *, include_tm_zone=True):
        zone, offset = timezone
        fix_struct = os.name == "nt" and sys.version_info < (3, 6)

        struct_time_attributes = [
            "tm_year",
            "tm_mon",
            "tm_mday",
            "tm_hour",
            "tm_min",
            "tm_sec",
            "tm_wday",
            "tm_yday",
            "tm_isdst",
            "tm_zone",
            "tm_gmtoff",
        ]

        if not include_tm_zone:
            struct_time_attributes.remove("tm_zone")
            struct_time_attributes.remove("tm_gmtoff")
            struct_time = namedtuple("struct_time", struct_time_attributes)._make
        elif fix_struct:
            struct_time = namedtuple("struct_time", struct_time_attributes)._make
        else:
            struct_time = time.struct_time

        freezegun_localtime = freezegun.api.fake_localtime

        def fake_localtime(t=None):
            struct = freezegun_localtime(t)
            override = {"tm_zone": zone, "tm_gmtoff": offset}
            attributes = []
            for attribute in struct_time_attributes:
                if attribute in override:
                    value = override[attribute]
                else:
                    value = getattr(struct, attribute)
                attributes.append(value)
            return struct_time(attributes)

        # Freezegun does not permit to override timezone name.
        monkeypatch.setattr(freezegun.api, "fake_localtime", fake_localtime)

        ctimes = {}

        __open__ = builtins.open

        def patched_open(filepath, *args, **kwargs):
            if not os.path.exists(filepath):
                ctimes[filepath] = datetime.datetime.now().timestamp()
            return __open__(filepath, *args, **kwargs)

        with freezegun.freeze_time(date) as frozen, monkeypatch.context() as context:
            context.setattr(loguru._file_sink, "get_ctime", ctimes.__getitem__)
            context.setattr(loguru._file_sink, "set_ctime", ctimes.__setitem__)
            context.setattr(builtins, "open", patched_open)
            yield frozen

    return freeze_time


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
    getframe_ = loguru._get_frame.load_get_frame_function()

    def patched_getframe(*args, **kwargs):
        frame = getframe_(*args, **kwargs)
        frame.f_globals.pop("__name__", None)
        return frame

    monkeypatch.setattr(loguru._logger, "get_frame", patched_getframe)
