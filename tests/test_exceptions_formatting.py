import os.path
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
    if sys.platform == "win32":
        exception = re.sub(
            r'File[^"]+"[^"]+\.py[^"]*"', lambda m: m.group().replace("\\", "/"), exception
        )
        exception = re.sub(r"(\r\n|\r|\n)", "\n", exception)

    exception = re.sub(r'"[^"]*usersite/lib.py"', '"usersite/lib.py"', exception)

    exception = re.sub(r"\b0x[0-9a-fA-F]+\b", "0xDEADBEEF", exception)

    if platform.python_implementation() == "PyPy":
        exception = exception.replace(
            "<function str.isdigit at 0xDEADBEEF>", "<method 'isdigit' of 'str' objects>"
        ).replace(
            "<function NoneType.__bool__ at 0xDEADBEEF>",
            "<slot wrapper '__bool__' of 'NoneType' objects>",
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
    filepath = os.path.join("tests", "exceptions", dirname, filename + ".py")
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
        "truncating",
        "unprintable_object",
    ],
)
def test_diagnose(filename):
    compare_exception("diagnose", filename)


@pytest.mark.parametrize(
    "filename", ["callback", "direct", "indirect", "string_lib", "string_source"]
)
def test_exception_ownership(filename):
    compare_exception("ownership", filename)


@pytest.mark.parametrize("diagnose", [False, True])
def test_carret_not_masked(writer, diagnose):
    logger.add(writer, backtrace=True, diagnose=diagnose, colorize=False, format="")

    @logger.catch
    def f(n):
        1 / n
        f(n - 1)

    f(30)

    assert sum(line.startswith("> ") for line in writer.read().splitlines()) == 1


@pytest.mark.parametrize("diagnose", [False, True])
def test_no_carret_if_no_backtrace(writer, diagnose):
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
    err = object()

    def writer(msg):
        nonlocal err
        err = msg.record["exception"]

    logger.add(writer)

    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("Exception")

    type_, value, traceback = err

    assert type_ == ZeroDivisionError
    assert isinstance(value, ZeroDivisionError)
    assert isinstance(traceback, types.TracebackType)
