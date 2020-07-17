import asyncio
import distutils.sysconfig
import site
import sys
import sysconfig
import types

import pytest

import loguru
from loguru import logger


@pytest.mark.parametrize("diagnose", [False, True])
def test_caret_not_masked(writer, diagnose):
    logger.add(writer, backtrace=True, diagnose=diagnose, colorize=False, format="")

    @logger.catch
    def f(n):
        1 / n
        f(n - 1)

    f(30)

    assert sum(line.startswith("> ") for line in writer.read().splitlines()) == 1


@pytest.mark.parametrize("diagnose", [False, True])
def test_no_caret_if_no_backtrace(writer, diagnose):
    logger.add(writer, backtrace=False, diagnose=diagnose, colorize=False, format="")

    @logger.catch
    def f(n):
        1 / n
        f(n - 1)

    f(30)

    assert sum(line.startswith("> ") for line in writer.read().splitlines()) == 0


@pytest.mark.parametrize("encoding", ["ascii", "UTF8", None, "unknown-encoding", "", object()])
def test_sink_encoding(writer, encoding):
    class Writer:
        def __init__(self, encoding):
            self.encoding = encoding
            self.output = ""

        def write(self, message):
            self.output += message

    writer = Writer(encoding)
    logger.add(writer, backtrace=True, diagnose=True, colorize=False, format="", catch=False)

    def foo(a, b):
        a / b

    def bar(c):
        foo(c, 0)

    try:
        bar(4)
    except ZeroDivisionError:
        logger.exception("")

    assert writer.output.endswith("ZeroDivisionError: division by zero\n")


def test_file_sink_ascii_encoding(tmpdir):
    file = tmpdir.join("test.log")
    logger.add(str(file), format="", encoding="ascii", errors="backslashreplace", catch=False)
    a = "天"

    try:
        "天" * a
    except Exception:
        logger.exception("")

    logger.remove()
    result = file.read_text("ascii")
    assert result.count('"\\u5929" * a') == 1
    assert result.count("-> '\\u5929'") == 1


def test_file_sink_utf8_encoding(tmpdir):
    file = tmpdir.join("test.log")
    logger.add(str(file), format="", encoding="utf8", errors="strict", catch=False)
    a = "天"

    try:
        "天" * a
    except Exception:
        logger.exception("")

    logger.remove()
    result = file.read_text("utf8")
    assert result.count('"天" * a') == 1
    assert result.count("└ '天'") == 1


def test_has_sys_real_prefix(writer, monkeypatch):
    monkeypatch.setattr(sys, "real_prefix", "/foo/bar/baz", raising=False)
    logger.add(writer, backtrace=False, diagnose=True, colorize=False, format="")

    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("")

    assert writer.read().endswith("ZeroDivisionError: division by zero\n")


def test_no_sys_real_prefix(writer, monkeypatch):
    monkeypatch.delattr(sys, "real_prefix", raising=False)
    logger.add(writer, backtrace=False, diagnose=True, colorize=False, format="")

    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("")

    assert writer.read().endswith("ZeroDivisionError: division by zero\n")


def test_has_site_getsitepackages(writer, monkeypatch):
    monkeypatch.setattr(site, "getsitepackages", lambda: ["foo", "bar", "baz"], raising=False)
    logger.add(writer, backtrace=False, diagnose=True, colorize=False, format="")

    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("")

    assert writer.read().endswith("ZeroDivisionError: division by zero\n")


def test_no_site_getsitepackages(writer, monkeypatch):
    monkeypatch.delattr(site, "getsitepackages", raising=False)
    logger.add(writer, backtrace=False, diagnose=True, colorize=False, format="")

    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("")

    assert writer.read().endswith("ZeroDivisionError: division by zero\n")


def test_user_site_is_path(writer, monkeypatch):
    monkeypatch.setattr(site, "USER_SITE", "/foo/bar/baz")
    logger.add(writer, backtrace=False, diagnose=True, colorize=False, format="")

    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("")

    assert writer.read().endswith("ZeroDivisionError: division by zero\n")


def test_user_site_is_none(writer, monkeypatch):
    monkeypatch.setattr(site, "USER_SITE", None)
    logger.add(writer, backtrace=False, diagnose=True, colorize=False, format="")

    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("")

    assert writer.read().endswith("ZeroDivisionError: division by zero\n")


def test_sysconfig_get_path_return_path(writer, monkeypatch):
    monkeypatch.setattr(sysconfig, "get_path", lambda *a, **k: "/foo/bar/baz")
    logger.add(writer, backtrace=False, diagnose=True, colorize=False, format="")

    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("")

    assert writer.read().endswith("ZeroDivisionError: division by zero\n")


def test_sysconfig_get_path_return_none(writer, monkeypatch):
    monkeypatch.setattr(sysconfig, "get_path", lambda *a, **k: None)
    logger.add(writer, backtrace=False, diagnose=True, colorize=False, format="")

    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("")

    assert writer.read().endswith("ZeroDivisionError: division by zero\n")


def test_distutils_get_python_lib_return_path(writer, monkeypatch):
    monkeypatch.setattr(distutils.sysconfig, "get_python_lib", lambda *a, **k: "/foo/bar/baz")
    logger.add(writer, backtrace=False, diagnose=True, colorize=False, format="")

    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("")

    assert writer.read().endswith("ZeroDivisionError: division by zero\n")


def test_distutils_get_python_lib_raise_exception(writer, monkeypatch):
    def raising(*a, **k):
        raise distutils.sysconfig.DistutilsPlatformError()

    monkeypatch.setattr(distutils.sysconfig, "get_python_lib", raising)
    logger.add(writer, backtrace=False, diagnose=True, colorize=False, format="")

    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("")

    assert writer.read().endswith("ZeroDivisionError: division by zero\n")


def test_distutils_not_installed(writer, monkeypatch):
    monkeypatch.setitem(sys.modules, "distutils", None)
    monkeypatch.setitem(sys.modules, "distutils.errors", None)
    monkeypatch.setitem(sys.modules, "distutils.sysconfig", None)
    monkeypatch.delattr(loguru._better_exceptions, "distutils", raising=False)
    monkeypatch.delattr(loguru._better_exceptions, "distutils.errors", raising=False)
    monkeypatch.delattr(loguru._better_exceptions, "distutils.syconfig", raising=False)
    logger.add(writer, backtrace=False, diagnose=True, colorize=False, format="")

    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("")

    assert writer.read().endswith("ZeroDivisionError: division by zero\n")


def test_no_exception(writer):
    logger.add(writer, backtrace=False, diagnose=False, colorize=False, format="{message}")

    logger.exception("No Error.")

    assert writer.read() in (
        "No Error.\nNoneType\n",
        "No Error.\nNoneType: None\n",  # Old versions of Python 3.5
    )


def test_exception_is_none():
    err = object()

    def writer(msg):
        nonlocal err
        err = msg.record["exception"]

    logger.add(writer)

    logger.error("No exception")

    assert err is None


def test_exception_is_tuple():
    exception = None

    def writer(msg):
        nonlocal exception
        exception = msg.record["exception"]

    logger.add(writer, catch=False)

    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("Exception")
        reference = sys.exc_info()

    t_1, v_1, tb_1 = exception
    t_2, v_2, tb_2 = (x for x in exception)
    t_3, v_3, tb_3 = exception[0], exception[1], exception[2]
    t_4, v_4, tb_4 = exception.type, exception.value, exception.traceback

    assert isinstance(exception, tuple)
    assert len(exception) == 3
    assert exception == reference
    assert reference == exception
    assert not (exception != reference)
    assert not (reference != exception)
    assert all(t == ZeroDivisionError for t in (t_1, t_2, t_3, t_4))
    assert all(isinstance(v, ZeroDivisionError) for v in (v_1, v_2, v_3, v_4))
    assert all(isinstance(tb, types.TracebackType) for tb in (tb_1, tb_2, tb_3, tb_4))


@pytest.mark.parametrize(
    "exception", [ZeroDivisionError, ArithmeticError, (ValueError, ZeroDivisionError)]
)
def test_exception_not_raising(writer, exception):
    logger.add(writer)

    @logger.catch(exception)
    def a():
        1 / 0

    a()
    assert writer.read().endswith("ZeroDivisionError: division by zero\n")


@pytest.mark.parametrize("exception", [ValueError, ((SyntaxError, TypeError))])
def test_exception_raising(writer, exception):
    logger.add(writer)

    @logger.catch(exception=exception)
    def a():
        1 / 0

    with pytest.raises(ZeroDivisionError):
        a()

    assert writer.read() == ""


@pytest.mark.parametrize(
    "exclude", [ZeroDivisionError, ArithmeticError, (ValueError, ZeroDivisionError)]
)
@pytest.mark.parametrize("exception", [BaseException, ZeroDivisionError])
def test_exclude_exception_raising(writer, exclude, exception):
    logger.add(writer)

    @logger.catch(exception, exclude=exclude)
    def a():
        1 / 0

    with pytest.raises(ZeroDivisionError):
        a()

    assert writer.read() == ""


@pytest.mark.parametrize("exclude", [ValueError, ((SyntaxError, TypeError))])
@pytest.mark.parametrize("exception", [BaseException, ZeroDivisionError])
def test_exclude_exception_not_raising(writer, exclude, exception):
    logger.add(writer)

    @logger.catch(exception, exclude=exclude)
    def a():
        1 / 0

    a()
    assert writer.read().endswith("ZeroDivisionError: division by zero\n")


def test_reraise(writer):
    logger.add(writer)

    @logger.catch(reraise=True)
    def a():
        1 / 0

    with pytest.raises(ZeroDivisionError):
        a()

    assert writer.read().endswith("ZeroDivisionError: division by zero\n")


def test_onerror(writer):
    is_error_valid = False
    logger.add(writer, format="{message}")

    def onerror(error):
        nonlocal is_error_valid
        logger.info("Called after logged message")
        _, exception, _ = sys.exc_info()
        is_error_valid = (error == exception) and isinstance(error, ZeroDivisionError)

    @logger.catch(onerror=onerror)
    def a():
        1 / 0

    a()

    assert is_error_valid
    assert writer.read().endswith(
        "ZeroDivisionError: division by zero\n" "Called after logged message\n"
    )


def test_onerror_with_reraise(writer):
    called = False
    logger.add(writer, format="{message}")

    def onerror(_):
        nonlocal called
        called = True

    with pytest.raises(ZeroDivisionError):
        with logger.catch(onerror=onerror, reraise=True):
            1 / 0

    assert called


def test_decorate_function(writer):
    logger.add(writer, format="{message}", diagnose=False, backtrace=False, colorize=False)

    @logger.catch
    def a(x):
        return 100 / x

    assert a(50) == 2
    assert writer.read() == ""


def test_decorate_coroutine(writer):
    logger.add(writer, format="{message}", diagnose=False, backtrace=False, colorize=False)

    @logger.catch
    async def foo(a, b):
        return a + b

    result = asyncio.run(foo(100, 5))

    assert result == 105
    assert writer.read() == ""


def test_decorate_generator(writer):
    @logger.catch
    def foo(x, y, z):
        yield x
        yield y
        return z

    f = foo(1, 2, 3)
    assert next(f) == 1
    assert next(f) == 2

    with pytest.raises(StopIteration, match=r"3"):
        next(f)


def test_decorate_generator_with_error():
    @logger.catch
    def foo():
        for i in range(3):
            1 / (2 - i)
            yield i

    assert list(foo()) == [0, 1]


def test_default_with_function():
    @logger.catch(default=42)
    def foo():
        1 / 0

    assert foo() == 42


def test_default_with_generator():
    @logger.catch(default=42)
    def foo():
        yield 1 / 0

    with pytest.raises(StopIteration, match=r"42"):
        next(foo())


def test_default_with_coroutine():
    @logger.catch(default=42)
    async def foo():
        return 1 / 0

    assert asyncio.run(foo()) == 42
