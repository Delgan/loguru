import pytest
import textwrap
from loguru import logger


def test_handler_formatting_with_decorator(writer):
    logger.add(writer, format="{name} {file.name} {function} {line}")

    @logger.catch
    def a():
        1 / 0

    a()

    assert writer.read().startswith(
        "tests.test_catch_wrapper test_catch_wrapper.py test_handler_formatting_with_decorator 13\n"
    )
    assert writer.read().endswith("ZeroDivisionError: division by zero\n")


def test_handler_formatting_with_context_manager(writer):
    logger.add(writer, format="{name} {file.name} {function} {line}")

    def a():
        with logger.catch():
            1 / 0

    a()

    assert writer.read().startswith("tests.test_catch_wrapper test_catch_wrapper.py a 26\n")
    assert writer.read().endswith("ZeroDivisionError: division by zero\n")


def test_message_formatting_with_decorator(writer):
    logger.add(writer, format="{message}")

    @logger.catch(message="{record[name]} {record[file].name} {record[function]} {record[line]}")
    def a():
        1 / 0

    a()

    assert writer.read().startswith(
        "tests.test_catch_wrapper test_catch_wrapper.py test_message_formatting_with_decorator 41\n"
    )
    assert writer.read().endswith("ZeroDivisionError: division by zero\n")


def test_message_formatting_with_context_manager(writer):
    logger.add(writer, format="{message}")

    def a():
        with logger.catch(
            message="{record[name]} {record[file].name} {record[function]} {record[line]}"
        ):
            1 / 0

    a()

    assert writer.read().startswith("tests.test_catch_wrapper test_catch_wrapper.py a 56\n")
    assert writer.read().endswith("ZeroDivisionError: division by zero\n")


def test_decorator_with_parentheses(writer):
    logger.add(writer)

    @logger.catch()
    def c(a, b):
        a / b

    c(5, b=0)

    assert writer.read().endswith("ZeroDivisionError: division by zero\n")


def test_decorator_without_parentheses(writer):
    logger.add(writer)

    @logger.catch
    def c(a, b=0):
        a / b

    c(2)

    assert writer.read().endswith("ZeroDivisionError: division by zero\n")


def test_context_manager(writer):
    logger.add(writer)

    with logger.catch():
        1 / 0

    assert writer.read().endswith("ZeroDivisionError: division by zero\n")


def test_function(writer):
    logger.add(writer)

    def a():
        1 / 0

    a = logger.catch()(a)
    a()

    assert writer.read().endswith("ZeroDivisionError: division by zero\n")


def test_with_and_without_backtrace(writer):
    logger.add(writer, backtrace=True)

    def c():
        a = 2
        b = 0
        a / b

    decorated = logger.catch()(c)
    decorated()

    result_with = writer.read()

    logger.remove()
    writer.clear()

    logger.add(writer, backtrace=False)

    decorated = logger.catch()(c)
    decorated()

    result_without = writer.read()

    assert len(result_with.splitlines()) > len(result_without.splitlines())
    assert result_with.endswith("ZeroDivisionError: division by zero\n")
    assert result_without.endswith("ZeroDivisionError: division by zero\n")


@pytest.mark.parametrize("exception", [ZeroDivisionError, (ZeroDivisionError, ValueError)])
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


def test_message(writer):
    logger.add(writer, format="{message}")
    message = "An error occurred:"

    def a():
        1 / 0

    a = logger.catch(message=message)(a)
    a()

    assert writer.read().startswith(message + "\n")
    assert writer.read().endswith("ZeroDivisionError: division by zero\n")


def test_level_name(writer):
    logger.add(writer, format="{level.name} | {level.no}")

    def a():
        with logger.catch(level="DEBUG"):
            1 / 0

    a()

    assert writer.read().startswith("DEBUG | 10\n")
    assert writer.read().endswith("ZeroDivisionError: division by zero\n")


def test_level_number(writer):
    logger.add(writer, format="{level.name} | {level.no}")

    def a():
        with logger.catch(level=13):
            1 / 0

    a()

    assert writer.read().startswith("Level 13 | 13\n")
    assert writer.read().endswith("ZeroDivisionError: division by zero\n")


def test_reraise(writer):
    logger.add(writer)

    @logger.catch(reraise=True)
    def a():
        1 / 0

    with pytest.raises(ZeroDivisionError):
        a()

    assert writer.read().endswith("ZeroDivisionError: division by zero\n")


def test_not_raising(writer):
    logger.add(writer, format="{message}")
    message = "It's ok"

    def a():
        logger.debug(message)

    a = logger.catch()(a)
    a()

    assert writer.read() == message + "\n"


def test_return_writer(writer):
    logger.add(writer, format="{message}")

    @logger.catch
    def a(x):
        return 100 / x

    result = a(50)

    assert writer.read() == ""
    assert result == 2
