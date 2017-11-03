import pytest
import traceback

@pytest.mark.parametrize('args, kwargs', [
    ([], {}),
    ([2, 0], {}),
    ([4], {'b': 0}),
    ([], {'a': 8}),
])
def test_wrapped(logger, writer, args, kwargs):
    logger.log_to(writer)

    @logger.catch
    def c(a=1, b=0):
        a / b

    c(*args, **kwargs)

    assert writer.read().endswith('ZeroDivisionError: division by zero\n')

def test_wrapped_better_exceptions(logger, writer):
    logger.log_to(writer, better_exceptions=True)

    @logger.catch()
    def c():
        a = 2
        b = 0
        a / b

    c()

    result_with = writer.read().strip()

    logger.stop()
    writer.clear()

    logger.log_to(writer, better_exceptions=False)

    @logger.catch()
    def c():
        a = 2
        b = 0
        a / b

    c()

    result_without = writer.read().strip()

    assert len(result_with) > len(result_without)

def test_custom_message(logger, writer):
    logger.log_to(writer, format='{message}')

    @logger.catch(message='An error occured:')
    def a():
        1 / 0

    a()

    assert writer.read().startswith('An error occured:\n')

def test_reraise(logger, writer):
    logger.log_to(writer)

    @logger.catch(reraise=True)
    def a():
        1 / 0

    with pytest.raises(ZeroDivisionError):
        a()

    assert writer.read().endswith('ZeroDivisionError: division by zero\n')

@pytest.mark.parametrize('exception, should_raise', [
    (ZeroDivisionError, False),
    (ValueError, True),
    ((ZeroDivisionError, ValueError), False),
    ((SyntaxError, TypeError), True),
])
@pytest.mark.parametrize('keyword', [True, False])
def test_exception(logger, writer, exception, should_raise, keyword):
    logger.log_to(writer)

    if keyword:
        @logger.catch(exception=exception)
        def a():
            1 / 0
    else:
        @logger.catch(exception)
        def a():
            1 / 0

    if should_raise:
        with pytest.raises(ZeroDivisionError):
            a()
        assert writer.read() == ''
    else:
        a()
        assert writer.read().endswith('ZeroDivisionError: division by zero\n')

@pytest.mark.xfail
def test_custom_level(logger, writter):
    logger.log_to(writer)

    @logger.catch(level=10)
    def a():
        1 / 0

    a()
