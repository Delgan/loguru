# coding: utf-8

import loguru

import pytest


@pytest.fixture
def logger():
    return loguru.Logger()

@pytest.fixture
def writter():

    def w(message):
        w.written.append(message)

    w.written = []
    w.read = lambda: ''.join(w.written)

    return w


@pytest.mark.parametrize('level, function, should_output', [
    (0,              lambda x: x.trace,    True),
    (loguru.TRACE,   lambda x: x.debug,    True),
    (loguru.INFO,    lambda x: x.info,     True),
    (loguru.WARNING, lambda x: x.success,  False),
    (float('inf'),   lambda x: x.critical, False),
])
def test_level_option(level, function, should_output, logger, writter):
    message = "Test Level"
    logger.log_to(writter, level=level, format='{message}')
    function(logger)(message)
    assert writter.read() == (message + '\n') * should_output


@pytest.mark.parametrize('message, format, expected', [
    ('a', 'Message: {message}', 'Message: a'),
    ('b', 'Nope', 'Nope'),
    ('c', '{level} {message} {level}', 'DEBUG c DEBUG'),
    ('d', '{message} {level} {level.no} {level.name}', 'd DEBUG %d DEBUG' % loguru.DEBUG)
])
def test_format_option(message, format, expected, logger, writter):
    logger.log_to(writter, format=format)
    logger.debug(message)
    assert writter.read() == expected + '\n'

@pytest.mark.parametrize('filter, should_output', [
    (None, True),
    ('tests', True),
    ('nope', False),
    ('testss', False),
    ('', True),
    (lambda r: True, True),
    (lambda r: False, False),
    (lambda r: r['level'] == "DEBUG", True),
    (lambda r: r['level'].no != loguru.DEBUG, False),
])
def test_filter_option(filter, should_output, logger, writter):
    message = "Test Filter"
    logger.log_to(writter, filter=filter, format='{message}')
    logger.debug(message)
    assert writter.read() == (message + '\n') * should_output

@pytest.mark.parametrize('message, format, expected, colored', [
    ('a', '<red>{message}</red>', 'a', False),
    ('b', '<red>{message}</red>', '\x1b[31mb\x1b[0m', True),
])
def test_colored_option(message, format, expected, colored, logger, writter):
    logger.log_to(writter, format=format, colored=colored)
    logger.debug(message)
    assert writter.read() == expected + '\n'

@pytest.mark.parametrize('better_exceptions, startswith', [
    (False, 'Traceback (most recent call last):\n  File'),
    (True, 'Traceback (most recent call last):\n\n  File'),
])
def test_better_exceptions_option(better_exceptions, startswith, logger, writter):
    logger.log_to(writter, format='{message}', better_exceptions=better_exceptions)
    try:
        1 / 0
    except:
        logger.exception('')
    assert writter.read().startswith('\n' + startswith)
