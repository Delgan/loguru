import os.path
import re
import subprocess
import sys

import pytest

from loguru import logger


def normalize(formatted_exception):
    """Normalize exception output for reproducible test cases"""
    if sys.platform == "win32":
        formatted_exception = re.sub(
            r'File[^"]+"[^"]+\.py[^"]*"',
            lambda m: m.group().replace("\\", "/"),
            formatted_exception,
        )
        formatted_exception = re.sub(r"(\r\n|\r|\n)", "\n", formatted_exception)
    formatted_exception = re.sub(r"\b0x[0-9a-fA-F]+\b", "0xDEADBEEF", formatted_exception)
    return formatted_exception


def generate(output, outpath):  # pragma: no cover
    """Generate new output file if exception formatting is updated"""
    with open(outpath, "w") as file:
        file.write(output)


@pytest.mark.parametrize(
    "filename",
    [
        "chained_expression_direct",
        "chained_expression_indirect",
        "chaining_first",
        "chaining_second",
        "chaining_third",
        "colorize",
        "enqueue",
        "enqueue_with_others_handlers",
        "frame_values_backward",
        "frame_values_forward",
        "function",
        "head_recursion",
        "nested",
        "nested_wrapping",
        "not_enough_arguments",
        "no_tb",
        "raising_recursion",
        "suppressed_expression_direct",
        "suppressed_expression_indirect",
        "tail_recursion",
        "too_many_arguments",
    ],
)
def test_exceptions_formatting(filename):
    cwd = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    python = sys.executable or "python"
    filepath = os.path.join("tests", "exceptions", filename + ".py")
    outpath = os.path.abspath(os.path.join(cwd, "tests", "exceptions", "output", filename + ".txt"))

    with subprocess.Popen(
        [python, filepath],
        shell=False,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    ) as proc:
        stdout, stderr = proc.communicate()
        print(stderr, file=sys.stderr)
        assert proc.returncode == 0
        assert stdout == ""

    stderr = normalize(stderr)

    # generate(stderr, outpath)

    with open(outpath, "r") as file:
        assert stderr == file.read()


def test_carret_not_masked(writer):
    logger.add(writer, backtrace=True, colorize=False, format="")

    @logger.catch
    def f(n):
        1 / n
        f(n - 1)

    f(30)

    assert sum(line.startswith("> ") for line in writer.read().splitlines()) == 1


def test_no_exception(writer):
    logger.add(writer, backtrace=False, colorize=False, format="{message}")

    logger.exception("No Error.")

    assert writer.read() in (
        "No Error.\nNoneType\n",
        "No Error.\nNoneType: None\n",  # Old versions of Python 3.5
    )
