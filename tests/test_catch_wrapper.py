import pytest

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

@pytest.mark.parametrize('better_exceptions', [True, False])
def test_wrapped_better_exceptions(logger, writer, better_exceptions):
    logger.log_to(writer, better_exceptions=better_exceptions)

    @logger.catch()
    def c():
        a = 2
        b = 0
        a / b

    c()

    length = len(writer.read().splitlines())

    if better_exceptions:
        assert length == 15
    else:
        assert length == 7

def test_custom_message(logger, writer):
    logger.log_to(writer, format='{message}')

    @logger.catch(message='An error occured:')
    def a():
        1 / 0

    a()

    assert writer.read().startswith('An error occured:\n')

def test_re_raise(logger, writer):
    logger.log_to(writer)

    @logger.catch(re_raise=True)
    def a():
        1 / 0

    with pytest.raises(ZeroDivisionError):
        a()

    assert writer.read().endswith('ZeroDivisionError: division by zero\n')

@pytest.mark.parametrize('exception, should_raise', [
    (ZeroDivisionError, False),
    (ValueError, True),
    ((ZeroDivisionError, ValueError), False),
])
def test_exception(logger, writer, exception, should_raise):
    logger.log_to(writer)

    @logger.catch(exception=exception)
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
