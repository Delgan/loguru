import os
import platform
import re
import subprocess
import sys
import traceback
from unittest.mock import MagicMock

import pytest

from loguru import logger


def normalize(exception):
    """Normalize exception output for reproducible test cases"""
    if os.name == "nt":
        exception = re.sub(
            r'File[^"]+"[^"]+\.py[^"]*"', lambda m: m.group().replace("\\", "/"), exception
        )
        exception = re.sub(r"(\r\n|\r|\n)", "\n", exception)

    if sys.version_info >= (3, 9, 0):

        def fix_filepath(match):
            filepath = match.group(1)
            pattern = (
                r'((?:\x1b\[[0-9]*m)+)([^"]+?)((?:\x1b\[[0-9]*m)+)([^"]+?)((?:\x1b\[[0-9]*m)+)'
            )
            match = re.match(pattern, filepath)
            start_directory = os.path.dirname(os.path.dirname(__file__))
            if match:
                groups = list(match.groups())
                groups[1] = os.path.relpath(os.path.abspath(groups[1]), start_directory) + "/"
                relpath = "".join(groups)
            else:
                relpath = os.path.relpath(os.path.abspath(filepath), start_directory)
            return 'File "%s"' % relpath.replace("\\", "/")

        exception = re.sub(
            r'File "([^"]+\.py[^"]*)"',
            fix_filepath,
            exception,
        )

    if sys.version_info < (3, 9, 0):
        if "SyntaxError" in exception:
            exception = re.sub(r"(\n *)(\^ *\n)", r"\1 \2", exception)
        elif "IndentationError" in exception:
            exception = re.sub(r"\n *\^ *\n", "\n", exception)

    if sys.version_info < (3, 10, 0):
        for module, line_before, line_after in [
            ("handler_formatting_with_context_manager.py", 17, 16),
            ("message_formatting_with_context_manager.py", 13, 10),
        ]:
            if module not in exception:
                continue
            expression = r"^(__main__ %s a) %d\n" % (module, line_before)
            exception = re.sub(expression, r"\1 %d\n" % line_after, exception)

    exception = re.sub(
        r'"[^"]*/somelib/__init__.py"', '"/usr/lib/python/somelib/__init__.py"', exception
    )

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
    raise AssertionError("The method 'generate()' was called while running tests.")


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
        "keyword_argument",
        "multilines_repr",
        "no_error_message",
        "parenthesis",
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
        "exception_in_property",
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


@pytest.mark.parametrize(
    "filename, minimum_python_version",
    [
        ("type_hints", (3, 6)),
        ("positional_only_argument", (3, 8)),
        ("walrus_operator", (3, 8)),
        ("match_statement", (3, 10)),
        ("exception_group_catch", (3, 11)),
        ("notes", (3, 11)),
        ("grouped_simple", (3, 11)),
        ("grouped_nested", (3, 11)),
        ("grouped_with_cause_and_context", (3, 11)),
        ("grouped_as_cause_and_context", (3, 11)),
        ("grouped_max_length", (3, 11)),
        ("grouped_max_depth", (3, 11)),
        ("f_string", (3, 12)),  # Available since 3.6 but in 3.12 the lexer for f-string changed.
    ],
)
def test_exception_modern(filename, minimum_python_version):
    if sys.version_info < minimum_python_version:
        pytest.skip("Feature not supported in this Python version")

    compare_exception("modern", filename)


@pytest.mark.skipif(
    not (3, 7) <= sys.version_info < (3, 11), reason="No backport available or needed"
)
def test_group_exception_using_backport(writer):
    from exceptiongroup import ExceptionGroup

    logger.add(writer, backtrace=True, diagnose=True, colorize=False, format="")

    try:
        raise ExceptionGroup("Test", [ValueError(1), ValueError(2)])
    except Exception:
        logger.exception("")

    assert writer.read().strip().startswith("+ Exception Group Traceback (most recent call last):")


def test_invalid_format_exception_only_no_output(writer, monkeypatch):
    logger.add(writer, backtrace=True, diagnose=True, colorize=False, format="")

    with monkeypatch.context() as context:
        context.setattr(traceback, "format_exception_only", lambda _e, _v: [])
        error = ValueError(0)
        logger.opt(exception=error).error("Error")

        assert writer.read() == "\n"


def test_invalid_format_exception_only_indented_error_message(writer, monkeypatch):
    logger.add(writer, backtrace=True, diagnose=True, colorize=False, format="")

    with monkeypatch.context() as context:
        context.setattr(traceback, "format_exception_only", lambda _e, _v: ["    ValueError: 0\n"])
        error = ValueError(0)
        logger.opt(exception=error).error("Error")

        assert writer.read() == "\n    ValueError: 0\n"


@pytest.mark.skipif(sys.version_info < (3, 11), reason="No builtin GroupedException")
def test_invalid_grouped_exception_no_exceptions(writer):
    error = MagicMock(spec=ExceptionGroup)
    error.__cause__ = None
    error.__context__ = None
    error.__traceback__ = None

    logger.add(writer, backtrace=True, diagnose=True, colorize=False, format="")
    logger.opt(exception=error).error("Error")

    assert writer.read().strip().startswith("| unittest.mock.MagicMock:")
