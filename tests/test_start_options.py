import json
import pytest
import multiprocessing
from loguru import logger
import ansimarkup
import io

@pytest.mark.parametrize('level, function, should_output', [
    (0,              lambda x: x.trace,    True),
    ("TRACE",        lambda x: x.debug,    True),
    ("INFO",         lambda x: x.info,     True),
    (10,             lambda x: x.debug,    True),
    ("WARNING",      lambda x: x.success,  False),
    (50,             lambda x: x.error,    False),
])
def test_level(level, function, should_output, writer):
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
def test_format(message, format, expected, writer):
    logger.start(writer, format=format)
    logger.debug(message)
    assert writer.read() == expected + '\n'

@pytest.mark.parametrize('filter, should_output', [
    (None, True),
    ('', True),
    ('tests', True),
    ('test', False),
    ('testss', False),
    ('tests.', False),
    ('tests.test_start_options', True),
    ('tests.test_start_options.', False),
    ('test_start_options', False),
    ('.', False),
    (lambda r: True, True),
    (lambda r: False, False),
    (lambda r: r['level'] == "DEBUG", True),
    (lambda r: r['level'].no != 10, False),
])
def test_filter(filter, should_output, writer):
    message = "Test Filter"
    logger.start(writer, filter=filter, format='{message}')
    logger.debug(message)
    assert writer.read() == (message + '\n') * should_output

@pytest.mark.parametrize('message, format, expected, colored', [
    ('a', '<red>{message}</red>', 'a', False),
    ('b', '<red>{message}</red>', ansimarkup.parse("<red>b</red>"), True),
    ('<red>nope</red>', '{message}', '<red>nope</red>', True),
])
def test_colored(message, format, expected, colored, writer):
    logger.start(writer, format=format, colored=colored)
    logger.debug(message)
    assert writer.read() == expected + '\n'

def test_enhanced(writer):
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

@pytest.mark.parametrize('with_exception', [False, True])
def test_serialized(with_exception):
    record_dict = record_json = None

    def sink(message):
        nonlocal record_dict, record_json
        record_dict = message.record
        record_json = json.loads(message)['record']

    logger.configure(extra=dict(not_serializable=object()))
    logger.start(sink, format="{message}", wrapped=False, serialized=True)
    if not with_exception:
        logger.debug("Test")
    else:
        try:
            1 / 0
        except:
            logger.exception("Test")

    assert set(record_dict.keys()) == set(record_json.keys())

@pytest.mark.parametrize('with_exception', [False, True])
def test_queued(with_exception):
    import time
    x = []
    def sink(message):
        time.sleep(0.1)
        x.append(message)
    logger.start(sink, format='{message}', queued=True)
    if not with_exception:
        logger.debug("Test")
    else:
        try:
            1 / 0
        except:
            logger.exception("Test")
    assert len(x) == 0
    time.sleep(0.2)
    lines = x[0].strip().splitlines()
    assert lines[0] == "Test"
    if with_exception:
        assert lines[-1] == "ZeroDivisionError: division by zero"
        assert sum(line.startswith('> ') for line in lines) == 1

def test_wrapped():
    def sink(msg):
        raise 1 / 0
    logger.start(sink, wrapped=False)
    with pytest.raises(ZeroDivisionError):
        logger.debug("fail")

def test_function_with_kwargs():
    out = []
    def function(message, kw2, kw1):
        out.append(message + kw1 + 'a' + kw2)
    logger.start(function, format='{message}', kw1="1", kw2="2")
    logger.debug("msg")
    assert out == ["msg\n1a2"]

def test_class_with_kwargs():
    out = []
    class Writer:
        def __init__(self, kw2, kw1):
            self.end = kw1 + 'b' + kw2
        def write(self, m):
            out.append(m + self.end)
    logger.start(Writer, format='{message}', kw1="1", kw2="2")
    logger.debug("msg")
    assert out == ["msg\n1b2"]

def test_file_object_with_kwargs():
    class Writer:
        def __init__(self):
            self.out = ''
        def write(self, m, kw2, kw1):
            self.out += m + kw1 + 'c' + kw2
    writer = Writer()
    logger.start(writer, format='{message}', kw1="1", kw2="2")
    logger.debug("msg")
    assert writer.out == "msg\n1c2"

def test_file_mode_a(tmpdir):
    file = tmpdir.join("test.log")
    file.write("base\n")
    logger.start(file.realpath(), format="{message}", mode='a')
    logger.debug("msg")
    assert file.read() == "base\nmsg\n"

def test_file_mode_w(tmpdir):
    file = tmpdir.join("test.log")
    file.write("base\n")
    logger.start(file.realpath(), format="{message}", mode='w')
    logger.debug("msg")
    assert file.read() == "msg\n"

def test_file_buffering(tmpdir):
    file = tmpdir.join("test.log")
    logger.start(file.realpath(), format="{message}", buffering=-1)
    logger.debug("x" * (io.DEFAULT_BUFFER_SIZE // 2))
    assert file.read() == ""
    logger.debug("x" * (io.DEFAULT_BUFFER_SIZE * 2))
    assert file.read() != ""

def test_invalid_function_kwargs():
    def function(message, a="Y"):
        pass
    logger.start(function, b="X", wrapped=False)
    with pytest.raises(TypeError):
        logger.debug("Nope")

def test_invalid_class_kwargs():
    class Writer:
        pass
    with pytest.raises(TypeError):
        logger.start(Writer, keyword=123)

def test_invalid_file_object_kwargs():
    class Writer:
        def __init__(self):
            self.out = ''
        def write(self, m):
            pass
    writer = Writer()
    logger.start(writer, format='{message}', kw1="1", kw2="2", wrapped=False)
    with pytest.raises(TypeError):
        logger.debug("msg")

def test_invalid_file_kwargs():
    with pytest.raises(TypeError):
        logger.start("file.log", nope=123)

@pytest.mark.parametrize("level", ["foo", -1, 3.4, object()])
def test_invalid_level(writer, level):
    with pytest.raises(ValueError):
        logger.start(writer, level=level)

@pytest.mark.parametrize("format", [-1, 3.4, object()])
def test_invalid_format(writer, format):
    with pytest.raises(ValueError):
        logger.start(writer, format=format)

@pytest.mark.parametrize("filter", [-1, 3.4, object()])
def test_invalid_filter(writer, filter):
    with pytest.raises(ValueError):
        logger.start(writer, filter=filter)
