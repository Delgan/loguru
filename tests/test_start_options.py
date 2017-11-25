# coding: utf-8

import loguru
import json
import pytest


@pytest.mark.parametrize('level, function, should_output', [
    (0,              lambda x: x.trace,    True),
    ("TRACE",        lambda x: x.debug,    True),
    ("INFO",         lambda x: x.info,     True),
    (10,             lambda x: x.debug,    True),
    ("WARNING",      lambda x: x.success,  False),
    (50,             lambda x: x.error,    False),
])
def test_level_option(level, function, should_output, logger, writer):
    message = "Test Level"
    logger.start(writer, level=level, format='{message}')
    function(logger)(message)
    assert writer.read() == (message + '\n') * should_output

@pytest.mark.parametrize('message, format, expected', [
    ('a', 'Message: {message}', 'Message: a'),
    ('b', 'Nope', 'Nope'),
    ('c', '{level} {message} {level}', 'DEBUG c DEBUG'),
    ('d', '{message} {level} {level.no} {level.name}', 'd DEBUG %d DEBUG' % 10)
])
def test_format_option(message, format, expected, logger, writer):
    logger.start(writer, format=format)
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
    (lambda r: r['level'].no != 10, False),
])
def test_filter_option(filter, should_output, logger, writer):
    message = "Test Filter"
    logger.start(writer, filter=filter, format='{message}')
    logger.debug(message)
    assert writer.read() == (message + '\n') * should_output

@pytest.mark.parametrize('message, format, expected, colored', [
    ('a', '<red>{message}</red>', 'a', False),
    ('b', '<red>{message}</red>', '\x1b[31mb\x1b[0m', True),
])
def test_colored_option(message, format, expected, colored, logger, writer):
    logger.start(writer, format=format, colored=colored)
    logger.debug(message)
    assert writer.read() == expected + '\n'

def test_enhanced_option(logger, writer):
    logger.start(writer, format='{message}', enhanced=True)
    try:
        1 / 0
    except:
        logger.exception('')
    result_with = writer.read().strip()

    logger.stop()
    writer.clear()

    logger.start(writer, format='{message}', enhanced=False)
    try:
        1 / 0
    except:
        logger.exception('')
    result_without = writer.read().strip()

    assert len(result_with) > len(result_without)

@pytest.mark.parametrize('sink_type', ['function', 'class', 'file_object', 'str_a', 'str_w'])
@pytest.mark.parametrize('test_invalid', [False, True])
def test_kwargs_option(sink_type, test_invalid, logger, tmpdir, capsys):
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
        logger.start(writer, format='{message}', **kwargs)
        logger.debug(msg)

    if test_invalid:
        if sink_type in ('function', 'file_object'):
            test()
            out, err = capsys.readouterr()
            assert out == ""
            assert err.startswith("--- Logging error in Loguru ---")
        else:
            with pytest.raises(TypeError):
                test()
    else:
        test()
        assert validator()

def test_structured_option(logger, writer):
    logger.start(writer, format="{message}", structured=True)
    logger.extra['not_serializable'] = object()
    logger.debug("Test")
    json.loads(writer.read())
