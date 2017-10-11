# coding: utf-8

import loguru

import pytest


@pytest.fixture
def logger():
    return loguru.Logger()

@pytest.fixture
def writer():

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
def test_level_option(level, function, should_output, logger, writer):
    message = "Test Level"
    logger.log_to(writer, level=level, format='{message}')
    function(logger)(message)
    assert writer.read() == (message + '\n') * should_output


@pytest.mark.parametrize('message, format, expected', [
    ('a', 'Message: {message}', 'Message: a'),
    ('b', 'Nope', 'Nope'),
    ('c', '{level} {message} {level}', 'DEBUG c DEBUG'),
    ('d', '{message} {level} {level.no} {level.name}', 'd DEBUG %d DEBUG' % loguru.DEBUG)
])
def test_format_option(message, format, expected, logger, writer):
    logger.log_to(writer, format=format)
    logger.debug(message)
    assert writer.read() == expected + '\n'

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
def test_filter_option(filter, should_output, logger, writer):
    message = "Test Filter"
    logger.log_to(writer, filter=filter, format='{message}')
    logger.debug(message)
    assert writer.read() == (message + '\n') * should_output

@pytest.mark.parametrize('message, format, expected, colored', [
    ('a', '<red>{message}</red>', 'a', False),
    ('b', '<red>{message}</red>', '\x1b[31mb\x1b[0m', True),
])
def test_colored_option(message, format, expected, colored, logger, writer):
    logger.log_to(writer, format=format, colored=colored)
    logger.debug(message)
    assert writer.read() == expected + '\n'

@pytest.mark.parametrize('better_exceptions, startswith', [
    (False, 'Traceback (most recent call last):\n  File'),
    (True, 'Traceback (most recent call last):\n\n  File'),
])
def test_better_exceptions_option(better_exceptions, startswith, logger, writer):
    logger.log_to(writer, format='{message}', better_exceptions=better_exceptions)
    try:
        1 / 0
    except:
        logger.exception('')
    assert writer.read().startswith('\n' + startswith)


@pytest.mark.parametrize('sink_type', ['function', 'class', 'file_object', 'str_a', 'str_w'])
@pytest.mark.parametrize('test_invalid', [False, True])
def test_kwargs_option(sink_type, test_invalid, logger, tmpdir):
    msg = 'msg'
    kwargs = {'kw1': '1', 'kw2': '2'}

    if sink_type == 'function':
        out = []
        def function(message, kw2, kw1):
            out.append(message + kw1 + 'a' + kw2)

        writer = function
        validator = lambda: out == [msg + '\n1a2']

        if test_invalid:
            writer = lambda m: None
    elif sink_type == 'class':
        out = []
        class Writer:
            def __init__(self, kw2, kw1):
                self.end = kw1 + 'b' + kw2
            def write(self, m):
                out.append(m + self.end)

        writer = Writer
        validator = lambda: out == [msg + '\n1b2']

        if test_invalid:
            writer.__init__ = lambda s: None
    elif sink_type == 'file_object':
        class Writer:
            def __init__(self):
                self.out = ''
            def write(self, m, kw2, kw1):
                self.out += m + kw1 + 'c' + kw2

        writer = Writer()
        validator = lambda: writer.out == msg + '\n1c2'

        if test_invalid:
            writer.write = lambda m: None
    elif sink_type == 'str_a':
        kwargs = {'mode': 'a', 'encoding': 'ascii'}
        file = tmpdir.join('test.log')
        with file.open(mode='w', encoding='ascii') as f:
            f.write("This shouldn't be overwritten.")

        writer = file.realpath()
        validator = lambda: file.read() == "This shouldn't be overwritten." + msg + "\n"

        if test_invalid:
            kwargs = {"foo": 1, "bar": 2}
    elif sink_type == 'str_w':
        kwargs = {'mode': 'w', 'encoding': 'ascii'}
        file = tmpdir.join('test.log')
        with file.open(mode='w', encoding='ascii') as f:
            f.write("This should be overwritten.")

        writer = file.realpath()
        validator = lambda: file.read() == msg + "\n"

        if test_invalid:
            kwargs = {"foo": 1, "bar": 2}

    def test():
        logger.log_to(writer, format='{message}', **kwargs)
        logger.debug(msg)

    if test_invalid:
        with pytest.raises(TypeError):
            test()
    else:
        test()
        assert validator()
