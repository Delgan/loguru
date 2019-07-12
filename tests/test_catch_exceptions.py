import asyncio
import os
import platform
import re
import site
import subprocess
import sys
import types

import pytest

from loguru import logger


def normalize(exception):
    """Normalize exception output for reproducible test cases"""
    if os.name:
        exception = re.sub(
            r'File[^"]+"[^"]+\.py[^"]*"', lambda m: m.group().replace("\\", "/"), exception
        )
        exception = re.sub(r"(\r\n|\r|\n)", "\n", exception)

    exception = re.sub(r'"[^"]*usersite/lib.py"', '"usersite/lib.py"', exception)

    exception = re.sub(r"\b0x[0-9a-fA-F]+\b", "0xDEADBEEF", exception)

    if platform.python_implementation() == "PyPy":
        exception = (
            exception.replace(
                "<function str.isdigit at 0xDEADBEEF>", "<method 'isdigit' of 'str' objects>"
            )
            .replace(
                "<function coroutine.send at 0xDEADBEEF>", "<method 'send' of 'coroutine' objects>"
            )
            .replace(
                "<function NoneType.__bool__ at 0xDEADBEEF>",
                "<slot wrapper '__bool__' of 'NoneType' objects>",
            )
        )

    return exception


def generate(output, outpath):
    """Generate new output file if exception formatting is updated"""
    os.makedirs(os.path.dirname(outpath), exist_ok=True)
    with open(outpath, "w") as file:
        file.write(output)
    assert False  # Avoid forgetting to remove "generate()" inadvertently


def compare_exception(dirname, filename):
    cwd = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    python = sys.executable or "python"
    filepath = os.path.join("tests", "exceptions", "source", dirname, filename + ".py")
    outpath = os.path.join(cwd, "tests", "exceptions", "output", dirname, filename + ".txt")

    with subprocess.Popen(
        [python, filepath],
        shell=False,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        env=dict(os.environ, PYTHONPATH=cwd, PYTHONIOENCODING="utf8"),
    ) as proc:
        stdout, stderr = proc.communicate()
        print(stderr, file=sys.stderr)
        assert proc.returncode == 0
        assert stdout == ""
        assert stderr != ""

    stderr = normalize(stderr)

    # generate(stderr, outpath)

    with open(outpath, "r") as file:
        assert stderr == file.read()


@pytest.mark.parametrize(
    "filename",
    [
        "chained_expression_direct",
        "chained_expression_indirect",
        "chaining_first",
        "chaining_second",
        "chaining_third",
        "enqueue",
        "enqueue_with_others_handlers",
        "frame_values_backward",
        "frame_values_forward",
        "function",
        "head_recursion",
        "missing_attributes_traceback_objects",
        "nested",
        "nested_chained_catch_up",
        "nested_decorator_catch_up",
        "nested_explicit_catch_up",
        "nested_wrapping",
        "no_tb",
        "not_enough_arguments",
        "raising_recursion",
        "suppressed_expression_direct",
        "suppressed_expression_indirect",
        "tail_recursion",
        "too_many_arguments",
    ],
)
def test_backtrace(filename):
    compare_exception("backtrace", filename)


@pytest.mark.parametrize(
    "filename",
    [
        "assertion_error",
        "assertion_error_custom",
        "assertion_error_in_string",
        "attributes",
        "chained_both",
        "encoding",
        "global_variable",
        "indentation_error",
        "multilines_repr",
        "no_error_message",
        "source_multilines",
        "source_strings",
        "syntax_error",
        "syntax_highlighting",
        "truncating",
        "unprintable_object",
    ],
)
def test_diagnose(filename):
    compare_exception("diagnose", filename)


@pytest.mark.parametrize(
    "filename",
    [
        "assertion_from_lib",
        "assertion_from_local",
        "callback",
        "catch_decorator",
        "catch_decorator_from_lib",
        "decorated_callback",
        "direct",
        "indirect",
        "string_lib",
        "string_source",
        "syntaxerror",
    ],
)
def test_exception_ownership(filename):
    compare_exception("ownership", filename)


@pytest.mark.parametrize(
    "filename",
    [
        "assertionerror_without_traceback",
        "catch_as_context_manager",
        "catch_as_decorator_with_parentheses",
        "catch_as_decorator_without_parentheses",
        "catch_as_function",
        "catch_message",
        "exception_formatting_coroutine",
        "exception_formatting_function",
        "exception_formatting_generator",
        "handler_formatting_with_context_manager",
        "handler_formatting_with_decorator",
        "level_name",
        "level_number",
        "message_formatting_with_context_manager",
        "message_formatting_with_decorator",
        "nested_with_reraise",
        "syntaxerror_without_traceback",
        "sys_tracebacklimit",
        "sys_tracebacklimit_negative",
        "sys_tracebacklimit_none",
        "sys_tracebacklimit_unset",
        "zerodivisionerror_without_traceback",
    ],
)
def test_exception_others(filename):
    compare_exception("others", filename)


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


@pytest.mark.parametrize("encoding", ["ascii", "UTF8", None])
def test_sink_encoding(writer, encoding):
    writer.encoding = encoding
    logger.add(writer, backtrace=True, diagnose=True, colorize=False, format="")

    def foo(a, b):
        a / b

    def bar(c):
        foo(c, 0)

    try:
        bar(4)
    except ZeroDivisionError:
        logger.exception("")

    assert writer.read().endswith("ZeroDivisionError: division by zero\n")


def test_has_sys_real_prefix(writer, monkeypatch):
    monkeypatch.setattr(sys, "real_prefix", "/foo/bar/baz", raising=False)
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


def test_no_sys_real_prefix(writer, monkeypatch):
    monkeypatch.delattr(sys, "real_prefix", raising=False)
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


def test_exception_is_unpackable():
    called = False

    def writer(msg):
        nonlocal called
        type_, value, traceback = msg.record["exception"]
        assert type_ == ZeroDivisionError
        assert isinstance(value, ZeroDivisionError)
        assert isinstance(traceback, types.TracebackType)
        called = True

    logger.add(writer, catch=False)

    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("Exception")

    assert called


@pytest.mark.parametrize("exception", [ZeroDivisionError, (ValueError, ZeroDivisionError)])
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


def test_reraise(writer):
    logger.add(writer)

    @logger.catch(reraise=True)
    def a():
        1 / 0

    with pytest.raises(ZeroDivisionError):
        a()

    assert writer.read().endswith("ZeroDivisionError: division by zero\n")


def test_decorate_function(writer):
    logger.add(writer, format="{message}", diagnose=False, backtrace=False, colorize=False)

    @logger.catch
    def a(x):
        return 100 / x

    assert a(50) == 2
    assert writer.read() == ""


def test_decorate_coroutine(writer):
    @logger.catch
    async def foo(a, b):
        return a + b

    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(foo(100, 5))
    loop.close()

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
