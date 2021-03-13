import builtins
import datetime
import importlib
import os
import pathlib
import re
import sys
import tempfile
import time
from unittest.mock import MagicMock, PropertyMock

import pytest

import loguru
from loguru import logger


@pytest.fixture
def tmpdir_local(reset_logger):
    # Pytest 'tmpdir' creates directories in /tmp, but /tmp does not support xattr, tests would fail
    with tempfile.TemporaryDirectory(dir=".") as tempdir:
        yield pathlib.Path(tempdir)
        logger.remove()  # Deleting file not possible if still in use by Loguru


def reload_filesink_ctime_functions(monkeypatch):
    ctime_functions = importlib.reload(loguru._ctime_functions)
    monkeypatch.setattr(loguru._file_sink, "get_ctime", ctime_functions.get_ctime)
    monkeypatch.setattr(loguru._file_sink, "set_ctime", ctime_functions.set_ctime)


@pytest.fixture
def monkeypatch_filesystem(monkeypatch):
    def monkeypatch_filesystem(raising=None, crtime=None, patch_xattr=False, patch_win32=False):
        filesystem = {}
        __open__ = open
        __stat_result__ = os.stat_result
        __stat__ = os.stat

        class StatWrapper:
            def __init__(self, wrapped, timestamp=None):
                self._wrapped = wrapped
                self._timestamp = timestamp

            def __getattr__(self, name):
                if name == raising:
                    raise AttributeError
                if name == crtime:
                    return self._timestamp
                return getattr(self._wrapped, name)

        def patched_stat(filepath):
            stat = __stat__(filepath)
            wrapped = StatWrapper(stat, filesystem.get(os.path.abspath(filepath)))
            return wrapped

        def patched_open(filepath, *args, **kwargs):
            if not os.path.exists(filepath):
                filesystem[os.path.abspath(filepath)] = loguru._datetime.datetime.now().timestamp()
            return __open__(filepath, *args, **kwargs)

        def patched_setxattr(filepath, attr, val, *arg, **kwargs):
            filesystem[(os.path.abspath(filepath), attr)] = val

        def patched_getxattr(filepath, attr, *args, **kwargs):
            try:
                return filesystem[(os.path.abspath(filepath), attr)]
            except KeyError:
                raise OSError

        def patched_setctime(filepath, timestamp):
            filesystem[os.path.abspath(filepath)] = timestamp

        monkeypatch.setattr(os, "stat_result", StatWrapper(__stat_result__))
        monkeypatch.setattr(os, "stat", patched_stat)
        monkeypatch.setattr(builtins, "open", patched_open)

        if patch_xattr:
            monkeypatch.setattr(os, "setxattr", patched_setxattr, raising=False)
            monkeypatch.setattr(os, "getxattr", patched_getxattr, raising=False)

        if patch_win32:
            win32_setctime = MagicMock(SUPPORTED=True, setctime=patched_setctime)
            monkeypatch.setitem(sys.modules, "win32_setctime", win32_setctime)

        reload_filesink_ctime_functions(monkeypatch)

    return monkeypatch_filesystem


@pytest.fixture
def windows_filesystem(monkeypatch, monkeypatch_filesystem):
    monkeypatch.setattr(os, "name", "nt")
    monkeypatch_filesystem(raising="st_birthtime", crtime="st_ctime", patch_win32=True)


@pytest.fixture
def darwin_filesystem(monkeypatch, monkeypatch_filesystem):
    monkeypatch.setattr(os, "name", "posix")
    monkeypatch.delattr(os, "setxattr", raising=False)
    monkeypatch.delattr(os, "getxattr", raising=False)
    monkeypatch_filesystem(crtime="st_birthtime")


@pytest.fixture
def linux_filesystem(monkeypatch, monkeypatch_filesystem):
    monkeypatch.setattr(os, "name", "posix")
    monkeypatch_filesystem(raising="st_birthtime", crtime="st_mtime", patch_xattr=True)


@pytest.fixture
def linux_xattr_oserror_filesystem(monkeypatch, monkeypatch_filesystem):
    def raising(*args, **kwargs):
        raise OSError

    monkeypatch.setattr(os, "name", "posix")
    monkeypatch.setattr(os, "setxattr", raising, raising=False)
    monkeypatch.setattr(os, "getxattr", raising, raising=False)
    monkeypatch_filesystem(raising="st_birthtime", crtime="st_mtime")


@pytest.fixture
def linux_xattr_attributeerror_filesystem(monkeypatch, monkeypatch_filesystem):
    monkeypatch.setattr(os, "name", "posix")
    monkeypatch.delattr(os, "setxattr", raising=False)
    monkeypatch.delattr(os, "getxattr", raising=False)
    monkeypatch_filesystem(raising="st_birthtime", crtime="st_mtime")


def test_renaming(tmpdir):
    logger.add(str(tmpdir.join("file.log")), rotation=0, format="{message}")

    time.sleep(0.1)
    logger.debug("a")

    files = sorted(tmpdir.listdir())
    assert len(files) == 2
    assert re.match(r"file\.[0-9-_]+\.log", files[0].basename)
    assert files[1].basename == "file.log"
    assert files[0].read() == ""
    assert files[1].read() == "a\n"

    time.sleep(0.1)
    logger.debug("b")

    files = sorted(tmpdir.listdir())
    assert len(files) == 3
    assert all(re.match(r"file\.[0-9-_]+\.log", f.basename) for f in files[:2])
    assert files[2].basename == "file.log"
    assert files[0].read() == ""
    assert files[1].read() == "a\n"
    assert files[2].read() == "b\n"


def test_no_renaming(monkeypatch_date, tmpdir):
    monkeypatch_date(2018, 1, 1, 0, 0, 0, 0)
    logger.add(str(tmpdir.join("file_{time}.log")), rotation=0, format="{message}")

    monkeypatch_date(2019, 1, 1, 0, 0, 0, 0)
    logger.debug("a")
    assert tmpdir.join("file_2018-01-01_00-00-00_000000.log").read() == ""
    assert tmpdir.join("file_2019-01-01_00-00-00_000000.log").read() == "a\n"

    monkeypatch_date(2020, 1, 1, 0, 0, 0, 0)
    logger.debug("b")
    assert tmpdir.join("file_2018-01-01_00-00-00_000000.log").read() == ""
    assert tmpdir.join("file_2019-01-01_00-00-00_000000.log").read() == "a\n"
    assert tmpdir.join("file_2020-01-01_00-00-00_000000.log").read() == "b\n"


@pytest.mark.parametrize("size", [8, 8.0, 7.99, "8 B", "8e-6MB", "0.008 kiB", "64b"])
def test_size_rotation(monkeypatch_date, tmpdir, size):
    monkeypatch_date(2018, 1, 1, 0, 0, 0, 0)

    file = tmpdir.join("test_{time}.log")
    i = logger.add(str(file), format="{message}", rotation=size, mode="w")

    monkeypatch_date(2018, 1, 1, 0, 0, 1, 0)
    logger.debug("abcde")

    monkeypatch_date(2018, 1, 1, 0, 0, 2, 0)
    logger.debug("fghij")

    monkeypatch_date(2018, 1, 1, 0, 0, 3, 0)
    logger.debug("klmno")

    monkeypatch_date(2018, 1, 1, 0, 0, 4, 0)
    logger.remove(i)

    assert len(tmpdir.listdir()) == 3
    assert tmpdir.join("test_2018-01-01_00-00-00_000000.log").read() == "abcde\n"
    assert tmpdir.join("test_2018-01-01_00-00-02_000000.log").read() == "fghij\n"
    assert tmpdir.join("test_2018-01-01_00-00-03_000000.log").read() == "klmno\n"


@pytest.mark.parametrize(
    "when, hours",
    [
        # hours = [
        #   Should not trigger, should trigger, should not trigger, should trigger, should trigger
        # ]
        ("13", [0, 1, 20, 4, 24]),
        ("13:00", [0.2, 0.9, 23, 1, 48]),
        ("13:00:00", [0.5, 1.5, 10, 15, 72]),
        ("13:00:00.123456", [0.9, 2, 10, 15, 256]),
        ("11:00", [22.9, 0.2, 23, 1, 24]),
        ("w0", [11, 1, 24 * 7 - 1, 1, 24 * 7]),
        ("W0 at 00:00", [10, 24 * 7 - 5, 0.1, 24 * 30, 24 * 14]),
        ("W6", [24, 24 * 28, 24 * 5, 24, 364 * 24]),
        ("saturday", [25, 25 * 12, 0, 25 * 12, 24 * 8]),
        ("w6 at 00", [8, 24 * 7, 24 * 6, 24, 24 * 8]),
        (" W6 at 13 ", [0.5, 1, 24 * 6, 24 * 6, 365 * 24]),
        ("w2  at  11:00:00 AM", [48 + 22, 3, 24 * 6, 24, 366 * 24]),
        ("MoNdAy at 11:00:30.123", [22, 24, 24, 24 * 7, 24 * 7]),
        ("sunday", [0.1, 24 * 7 - 10, 24, 24 * 6, 24 * 7]),
        ("SUNDAY at 11:00", [1, 24 * 7, 2, 24 * 7, 30 * 12]),
        ("sunDAY at 1:0:0.0 pm", [0.9, 0.2, 24 * 7 - 2, 3, 24 * 8]),
        (datetime.time(15), [2, 3, 19, 5, 24]),
        (datetime.time(18, 30, 11, 123), [1, 5.51, 20, 24, 40]),
        ("2 h", [1, 2, 0.9, 0.5, 10]),
        ("1 hour", [0.5, 1, 0.1, 100, 1000]),
        ("7 days", [24 * 7 - 1, 1, 48, 24 * 10, 24 * 365]),
        ("1h 30 minutes", [1.4, 0.2, 1, 2, 10]),
        ("1 w, 2D", [24 * 8, 24 * 2, 24, 24 * 9, 24 * 9]),
        ("1.5d", [30, 10, 0.9, 48, 35]),
        ("1.222 hours, 3.44s", [1.222, 0.1, 1, 1.2, 2]),
        (datetime.timedelta(hours=1), [0.9, 0.2, 0.7, 0.5, 3]),
        (datetime.timedelta(minutes=30), [0.48, 0.04, 0.07, 0.44, 0.5]),
        ("hourly", [0.9, 0.2, 0.8, 3, 1]),
        ("daily", [11, 1, 23, 1, 24]),
        ("WEEKLY", [11, 2, 24 * 6, 24, 24 * 7]),
        ("mOnthLY", [0, 24 * 13, 29 * 24, 60 * 24, 24 * 35]),
        ("monthly", [10 * 24, 30 * 24 * 6, 24, 24 * 7, 24 * 31]),
        ("Yearly ", [100, 24 * 7 * 30, 24 * 300, 24 * 100, 24 * 400]),
    ],
)
def test_time_rotation(monkeypatch_date, darwin_filesystem, tmpdir, when, hours):
    now = datetime.datetime(2017, 6, 18, 12, 0, 0)  # Sunday

    monkeypatch_date(
        now.year, now.month, now.day, now.hour, now.minute, now.second, now.microsecond
    )

    i = logger.add(str(tmpdir.join("test_{time}.log")), format="{message}", rotation=when, mode="w")

    for h, m in zip(hours, ["a", "b", "c", "d", "e"]):
        now += datetime.timedelta(hours=h)
        monkeypatch_date(
            now.year, now.month, now.day, now.hour, now.minute, now.second, now.microsecond
        )
        logger.debug(m)

    logger.remove(i)
    assert [f.read() for f in sorted(tmpdir.listdir())] == ["a\n", "b\nc\n", "d\n", "e\n"]


def test_time_rotation_dst(monkeypatch_date, darwin_filesystem, tmpdir):
    monkeypatch_date(2018, 10, 27, 5, 0, 0, 0, "CET", 3600)
    i = logger.add(str(tmpdir.join("test_{time}.log")), format="{message}", rotation="1 day")
    logger.debug("First")

    monkeypatch_date(2018, 10, 28, 5, 30, 0, 0, "CEST", 7200)
    logger.debug("Second")

    monkeypatch_date(2018, 10, 29, 6, 0, 0, 0, "CET", 3600)
    logger.debug("Third")
    logger.remove(i)

    assert len(tmpdir.listdir()) == 3
    assert tmpdir.join("test_2018-10-27_05-00-00_000000.log").read() == "First\n"
    assert tmpdir.join("test_2018-10-28_05-30-00_000000.log").read() == "Second\n"
    assert tmpdir.join("test_2018-10-29_06-00-00_000000.log").read() == "Third\n"


@pytest.mark.parametrize("delay", [False, True])
def test_time_rotation_reopening_native(tmpdir_local, delay):
    filepath = str(tmpdir_local / "test.log")
    i = logger.add(filepath, format="{message}", delay=delay, rotation="1 s")
    logger.info("1")
    time.sleep(0.75)
    logger.info("2")
    logger.remove(i)
    i = logger.add(filepath, format="{message}", delay=delay, rotation="1 s")
    logger.info("3")

    assert len(list(tmpdir_local.iterdir())) == 1
    assert (tmpdir_local / "test.log").read_text() == "1\n2\n3\n"

    time.sleep(0.5)
    logger.info("4")

    assert len(list(tmpdir_local.iterdir())) == 2
    assert (tmpdir_local / "test.log").read_text() == "4\n"

    logger.remove(i)
    time.sleep(0.5)
    i = logger.add(filepath, format="{message}", delay=delay, rotation="1 s")
    logger.info("5")

    assert len(list(tmpdir_local.iterdir())) == 2
    assert (tmpdir_local / "test.log").read_text() == "4\n5\n"

    time.sleep(0.75)
    logger.info("6")
    logger.remove(i)

    assert len(list(tmpdir_local.iterdir())) == 3
    assert (tmpdir_local / "test.log").read_text() == "6\n"


def rotation_reopening(tmpdir, monkeypatch_date, delay):
    monkeypatch_date(2018, 10, 27, 5, 0, 0, 0)
    filepath = tmpdir.join("test.log")
    i = logger.add(str(filepath), format="{message}", delay=delay, rotation="2 h")
    logger.info("1")
    monkeypatch_date(2018, 10, 27, 6, 30, 0, 0)
    logger.info("2")
    logger.remove(i)
    i = logger.add(str(filepath), format="{message}", delay=delay, rotation="2 h")
    logger.info("3")

    assert len(tmpdir.listdir()) == 1
    assert filepath.read() == "1\n2\n3\n"

    monkeypatch_date(2018, 10, 27, 7, 30, 0, 0)
    logger.info("4")

    assert len(tmpdir.listdir()) == 2
    assert filepath.read() == "4\n"

    logger.remove(i)
    monkeypatch_date(2018, 10, 27, 8, 30, 0, 0)

    i = logger.add(str(filepath), format="{message}", delay=delay, rotation="2 h")
    logger.info("5")

    assert len(tmpdir.listdir()) == 2
    assert filepath.read() == "4\n5\n"

    monkeypatch_date(2018, 10, 27, 10, 0, 0, 0)
    logger.info("6")
    logger.remove(i)

    assert len(tmpdir.listdir()) == 3
    assert filepath.read() == "6\n"


@pytest.mark.parametrize("delay", [False, True])
def test_time_rotation_reopening_windows(tmpdir, monkeypatch_date, windows_filesystem, delay):
    rotation_reopening(tmpdir, monkeypatch_date, delay)


@pytest.mark.parametrize("delay", [False, True])
def test_time_rotation_reopening_darwin(tmpdir, monkeypatch_date, darwin_filesystem, delay):
    rotation_reopening(tmpdir, monkeypatch_date, delay)


@pytest.mark.parametrize("delay", [False, True])
def test_time_rotation_reopening_linux(tmpdir, monkeypatch_date, linux_filesystem, delay):
    rotation_reopening(tmpdir, monkeypatch_date, delay)


@pytest.mark.parametrize("delay", [False, True])
def test_time_rotation_reopening_linux_xattr_oserror(
    tmpdir, monkeypatch_date, linux_xattr_oserror_filesystem, delay
):
    rotation_reopening(tmpdir, monkeypatch_date, delay)


@pytest.mark.parametrize("delay", [False, True])
def test_time_rotation_reopening_linux_xattr_attributeerror(
    tmpdir, monkeypatch_date, linux_xattr_attributeerror_filesystem, delay
):
    rotation_reopening(tmpdir, monkeypatch_date, delay)


def test_time_rotation_windows_no_setctime(
    tmpdir, windows_filesystem, monkeypatch, monkeypatch_date
):
    SUPPORTED = PropertyMock(return_value=False)
    win32_setctime = MagicMock()
    type(win32_setctime).SUPPORTED = SUPPORTED
    monkeypatch.setitem(sys.modules, "win32_setctime", win32_setctime)

    reload_filesink_ctime_functions(monkeypatch)

    monkeypatch_date(2018, 10, 27, 5, 0, 0, 0)
    logger.add(str(tmpdir.join("test.{time}.log")), format="{message}", rotation="2 h")
    logger.info("1")
    monkeypatch_date(2018, 10, 27, 6, 30, 0, 0)
    logger.info("2")
    assert len(tmpdir.listdir()) == 1
    monkeypatch_date(2018, 10, 27, 7, 30, 0, 0)
    logger.info("3")
    assert len(tmpdir.listdir()) == 2
    assert tmpdir.join("test.2018-10-27_05-00-00_000000.log").read() == "1\n2\n"
    assert tmpdir.join("test.2018-10-27_07-30-00_000000.log").read() == "3\n"
    assert SUPPORTED.called
    assert not win32_setctime.setctime.called


@pytest.mark.parametrize("exception", [ValueError, OSError])
def test_time_rotation_windows_setctime_exception(
    tmpdir, windows_filesystem, monkeypatch, monkeypatch_date, exception
):
    setctime_called = False

    def raising_setctime(filepath, timestamp):
        nonlocal setctime_called
        setctime_called = True
        raise exception("Setctime error")

    win32_setctime = MagicMock(SUPPORTED=True, setctime=raising_setctime)
    monkeypatch.setitem(sys.modules, "win32_setctime", win32_setctime)

    reload_filesink_ctime_functions(monkeypatch)

    monkeypatch_date(2018, 10, 27, 5, 0, 0, 0)
    logger.add(str(tmpdir.join("test.{time}.log")), format="{message}", rotation="2 h")
    logger.info("1")
    monkeypatch_date(2018, 10, 27, 6, 30, 0, 0)
    logger.info("2")
    assert len(tmpdir.listdir()) == 1
    monkeypatch_date(2018, 10, 27, 7, 30, 0, 0)
    logger.info("3")
    assert len(tmpdir.listdir()) == 2
    assert tmpdir.join("test.2018-10-27_05-00-00_000000.log").read() == "1\n2\n"
    assert tmpdir.join("test.2018-10-27_07-30-00_000000.log").read() == "3\n"
    assert setctime_called


def test_function_rotation(monkeypatch_date, tmpdir):
    monkeypatch_date(2018, 1, 1, 0, 0, 0, 0)
    x = iter([False, True, False])
    logger.add(str(tmpdir.join("test_{time}.log")), rotation=lambda *_: next(x), format="{message}")
    logger.debug("a")
    assert tmpdir.join("test_2018-01-01_00-00-00_000000.log").read() == "a\n"

    monkeypatch_date(2019, 1, 1, 0, 0, 0, 0)
    logger.debug("b")
    assert tmpdir.join("test_2019-01-01_00-00-00_000000.log").read() == "b\n"

    monkeypatch_date(2020, 1, 1, 0, 0, 0, 0)
    logger.debug("c")

    assert len(tmpdir.listdir()) == 2
    assert tmpdir.join("test_2018-01-01_00-00-00_000000.log").read() == "a\n"
    assert tmpdir.join("test_2019-01-01_00-00-00_000000.log").read() == "b\nc\n"


@pytest.mark.parametrize("mode", ["w", "x"])
def test_rotation_at_remove(monkeypatch_date, tmpdir, mode):
    monkeypatch_date(2018, 1, 1, 0, 0, 0, 0)
    i = logger.add(
        str(tmpdir.join("test_{time:YYYY}.log")), rotation="10 MB", mode=mode, format="{message}"
    )
    logger.debug("test")
    logger.remove(i)

    assert len(tmpdir.listdir()) == 1
    assert tmpdir.join("test_2018.log").read() == "test\n"


@pytest.mark.parametrize("mode", ["a", "a+"])
def test_no_rotation_at_remove(tmpdir, mode):
    i = logger.add(str(tmpdir.join("test.log")), rotation="10 MB", mode=mode, format="{message}")
    logger.debug("test")
    logger.remove(i)

    assert len(tmpdir.listdir()) == 1
    assert tmpdir.join("test.log").read() == "test\n"


def test_rename_existing_with_creation_time(monkeypatch, tmpdir):
    def creation_time(filepath):
        assert os.path.isfile(filepath)
        assert os.path.basename(filepath) == "test.log"
        return datetime.datetime(2018, 1, 1, 0, 0, 0, 0).timestamp()

    logger.add(str(tmpdir.join("test.log")), rotation=10, format="{message}")
    logger.debug("X")

    monkeypatch.setattr(loguru._file_sink, "get_ctime", creation_time)

    logger.debug("Y" * 20)

    assert len(tmpdir.listdir()) == 2
    assert tmpdir.join("test.log").check(exists=1)
    assert tmpdir.join("test.2018-01-01_00-00-00_000000.log").check(exists=1)


def test_renaming_rotation_dest_exists(monkeypatch, monkeypatch_date, tmpdir):
    date = (2019, 1, 2, 3, 4, 5, 6)
    timestamp = datetime.datetime(*date).timestamp()
    monkeypatch_date(*date)
    monkeypatch.setattr(loguru._file_sink, "get_ctime", lambda _: timestamp)

    def rotate(file, msg):
        return True

    logger.add(str(tmpdir.join("rotate.log")), rotation=rotate, format="{message}")
    logger.info("A")
    logger.info("B")
    logger.info("C")
    assert len(tmpdir.listdir()) == 4
    assert tmpdir.join("rotate.log").read() == "C\n"
    assert tmpdir.join("rotate.2019-01-02_03-04-05_000006.log").read() == ""
    assert tmpdir.join("rotate.2019-01-02_03-04-05_000006.2.log").read() == "A\n"
    assert tmpdir.join("rotate.2019-01-02_03-04-05_000006.3.log").read() == "B\n"


def test_renaming_rotation_dest_exists_with_time(monkeypatch, monkeypatch_date, tmpdir):
    date = (2019, 1, 2, 3, 4, 5, 6)
    timestamp = datetime.datetime(*date).timestamp()
    monkeypatch_date(*date)
    monkeypatch.setattr(loguru._file_sink, "get_ctime", lambda _: timestamp)

    def rotate(file, msg):
        return True

    logger.add(str(tmpdir.join("rotate.{time}.log")), rotation=rotate, format="{message}")
    logger.info("A")
    logger.info("B")
    logger.info("C")
    assert len(tmpdir.listdir()) == 4
    assert tmpdir.join("rotate.2019-01-02_03-04-05_000006.log").read() == "C\n"
    assert (
        tmpdir.join("rotate.2019-01-02_03-04-05_000006.2019-01-02_03-04-05_000006.log").read() == ""
    )
    assert (
        tmpdir.join("rotate.2019-01-02_03-04-05_000006.2019-01-02_03-04-05_000006.2.log").read()
        == "A\n"
    )
    assert (
        tmpdir.join("rotate.2019-01-02_03-04-05_000006.2019-01-02_03-04-05_000006.3.log").read()
        == "B\n"
    )


def test_exception_during_rotation(tmpdir, capsys):
    raising = True

    def failing_rotation(_, __):
        nonlocal raising
        if raising:
            raising = False
            raise Exception("Rotation error")
        return False

    logger.add(
        str(tmpdir.join("test.log")), rotation=failing_rotation, format="{message}", catch=True
    )

    logger.info("A")
    logger.info("B")

    files = sorted(tmpdir.listdir())
    out, err = capsys.readouterr()

    len(files) == 1
    assert tmpdir.join("test.log").read() == "B\n"
    assert out == ""
    assert err.count("Logging error in Loguru Handler") == 1
    assert err.count("Exception: Rotation error") == 1


def test_exception_during_rotation_not_caught(tmpdir, capsys):
    raising = True

    def failing_rotation(_, __):
        nonlocal raising
        if raising:
            raising = False
            raise Exception("Rotation error")
        return False

    logger.add(
        str(tmpdir.join("test.log")), rotation=failing_rotation, format="{message}", catch=False
    )

    with pytest.raises(Exception, match=r"Rotation error"):
        logger.info("A")

    logger.info("B")

    files = sorted(tmpdir.listdir())
    out, err = capsys.readouterr()

    len(files) == 1
    assert tmpdir.join("test.log").read() == "B\n"
    assert out == err == ""


@pytest.mark.parametrize(
    "rotation", [object(), os, datetime.date(2017, 11, 11), datetime.datetime.now(), 1j]
)
def test_invalid_rotation(rotation):
    with pytest.raises(TypeError):
        logger.add("test.log", rotation=rotation)


@pytest.mark.parametrize(
    "rotation",
    [
        "w7",
        "w10",
        "w-1",
        "h",
        "M",
        "w1at13",
        "www",
        "13 at w2",
        "w",
        "K",
        "tufy MB",
        "111.111.111 kb",
        "3 Ki",
        "2017.11.12",
        "11:99",
        "monday at 2017",
        "e days",
        "2 days 8 pouooi",
        "foobar",
        "w5 at [not|a|time]",
        "[not|a|day] at 12:00",
        "__dict__",
    ],
)
def test_unknown_rotation(rotation):
    with pytest.raises(ValueError):
        logger.add("test.log", rotation=rotation)
