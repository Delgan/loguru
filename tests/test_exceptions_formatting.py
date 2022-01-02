import os
import platform
import re
import subprocess
import sys

import pytest


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
