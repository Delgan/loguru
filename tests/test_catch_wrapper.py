import pytest
import traceback

zero_division_error = 'ZeroDivisionError: division by zero\n'
use_decorator = pytest.mark.parametrize('use_decorator', [True, False])

@pytest.mark.parametrize('use_parentheses', [True, False])
def test_decorator(logger, writer, use_parentheses):
    logger.log_to(writer)

    if use_parentheses:
        @logger.catch()
        def c(a, b):
            a / b
        c(5, b=0)
    else:
        @logger.catch
        def c(a, b=0):
            a / b
        c(2)

    assert writer.read().endswith(zero_division_error)

@pytest.mark.parametrize('use_parentheses', [True, False])
def test_context_manager(logger, writer, use_parentheses):
    logger.log_to(writer)

    if use_parentheses:
        with logger.catch():
            1 / 0
    else:
        with logger.catch:
            1 / 0

    assert writer.read().endswith(zero_division_error)

def test_with_better_exceptions(logger, writer):
    logger.log_to(writer, better_exceptions=True)

    def c():
        a = 2
        b = 0
        a / b

    decorated = logger.catch(c)
    decorated()

    result_with = writer.read()

    logger.stop()
    writer.clear()

    logger.log_to(writer, better_exceptions=False)

    decorated = logger.catch(c)
    decorated()

    result_without = writer.read()

    assert len(result_with) > len(result_without)
    assert result_with.endswith(zero_division_error)
    assert result_without.endswith(zero_division_error)

@use_decorator
def test_custom_message(logger, writer, use_decorator):
    logger.log_to(writer, format='{message}')
    message = 'An error occured:'

    if use_decorator:
        @logger.catch(message=message)
        def a():
            1 / 0
        a()
    else:
        with logger.catch(message=message):
            1 / 0

    assert writer.read().startswith(message + '\n')

@use_decorator
def test_reraise(logger, writer, use_decorator):
    logger.log_to(writer)

    if use_decorator:
        @logger.catch(reraise=True)
        def a():
            1 / 0
    else:
        def a():
            with logger.catch(reraise=True):
                1 / 0

    with pytest.raises(ZeroDivisionError):
        a()

    assert writer.read().endswith(zero_division_error)

@pytest.mark.parametrize('exception, should_raise', [
    (ZeroDivisionError, False),
    (ValueError, True),
    ((ZeroDivisionError, ValueError), False),
    ((SyntaxError, TypeError), True),
])
@pytest.mark.parametrize('keyword', [True, False])
@use_decorator
def test_exception(logger, writer, exception, should_raise, keyword, use_decorator):
    logger.log_to(writer)

    if keyword:
        if use_decorator:
            @logger.catch(exception=exception)
            def a():
                1 / 0
        else:
            def a():
                with logger.catch(exception=exception):
                    1 / 0
    else:
        if use_decorator:
            @logger.catch(exception)
            def a():
                1 / 0
        else:
            def a():
                with logger.catch(exception):
                    1 / 0

    if should_raise:
        with pytest.raises(ZeroDivisionError):
            a()
        assert writer.read() == ''
    else:
        a()
        assert writer.read().endswith(zero_division_error)

@use_decorator
def test_not_raising(logger, writer, use_decorator):
    logger.log_to(writer, format='{message}')
    message = "It's ok"

    if use_decorator:
        @logger.catch
        def a():
            logger.debug(message)
        a()
    else:
        with logger.catch:
            logger.debug(message)

    assert writer.read() == message + '\n'

@pytest.mark.xfail
@use_decorator
def test_custom_level(logger, writter, use_decorator):
    logger.log_to(writer)

    if use_decorator:
        @logger.catch(level=10)
        def a():
            1 / 0
    else:
        def a():
            with logger.catch(level=10):
                1 / 0

    a()
