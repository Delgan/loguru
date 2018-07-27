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
    ('a', 'Message: {message}', 'Message: a\n'),
    ('b', 'Nope', 'Nope\n'),
    ('c', '{level} {message} {level}', 'DEBUG c DEBUG\n'),
    ('d', '{message} {level} {level.no} {level.name}', 'd DEBUG 10 DEBUG\n'),
    ('e', lambda _: '{message}', 'e'),
    ('f', lambda r: '{message} ' + r['level'].name, 'f DEBUG'),
])
def test_format(message, format, expected, writer):
    logger.start(writer, format=format)
    logger.debug(message)
    assert writer.read() == expected

def test_progressive_format(writer):
    def formatter(record):
        if record['extra'].get("progessive", False):
            fmt = "{message}"
        else:
            fmt = "[{level.name}] {message}"
        return fmt + record['extra'].get("end", "\n")
    logger.start(writer, format=formatter)
    logger.bind(end=" ").debug("Start:")
    for _ in range(5):
        logger.bind(progessive=True, end="").debug(".")
    logger.bind(progessive=True).debug("")
    logger.debug("End")
    assert writer.read() == ("[DEBUG] Start: .....\n"
                             "[DEBUG] End\n")

def test_function_format_without_exception(writer):
    logger.start(writer, format=lambda _: '{message}\n')
    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("Error!")
    assert writer.read() == "Error!\n"

def test_function_format_with_exception(writer):
    logger.start(writer, format=lambda _: '{message}\n{exception}')
    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("Error!")
    lines = writer.read().splitlines()
    assert lines[0] == "Error!"
    assert lines[-1] == "ZeroDivisionError: division by zero"

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

@pytest.mark.parametrize('message, format, expected, colorize', [
    ('a', '<red>{message}</red>', 'a\n', False),
    ('b', '<red>{message}</red>', ansimarkup.parse("<red>b</red>\n"), True),
    ('c', lambda _: '<red>{message}</red>', 'c', False),
    ('d', lambda _: '<red>{message}</red>', ansimarkup.parse('<red>d</red>'), True),
    ('<red>nope</red>', '{message}', '<red>nope</red>\n', True),
])
def test_colorize(message, format, expected, colorize, writer):
    logger.start(writer, format=format, colorize=colorize)
    logger.debug(message)
    assert writer.read() == expected

def test_enhance(writer):
    logger.start(writer, format='{message}', enhance=True)
    try:
        1 / 0
    except:
        logger.exception('')
    result_with = writer.read().strip()

    logger.stop()
    writer.clear()

    logger.start(writer, format='{message}', enhance=False)
    try:
        1 / 0
    except:
        logger.exception('')
    result_without = writer.read().strip()

    assert len(result_with) > len(result_without)

@pytest.mark.parametrize('with_exception', [False, True])
def test_serialize(with_exception):
    record_dict = record_json = None

    def sink(message):
        nonlocal record_dict, record_json
        record_dict = message.record
        record_json = json.loads(message)['record']

    logger.configure(extra=dict(not_serializable=object()))
    logger.start(sink, format="{message}", catch=False, serialize=True)
    if not with_exception:
        logger.debug("Test")
    else:
        try:
            1 / 0
        except:
            logger.exception("Test")

    assert set(record_dict.keys()) == set(record_json.keys())

@pytest.mark.parametrize('with_exception', [False, True])
def test_enqueue(with_exception):
    import time
    x = []
    def sink(message):
        time.sleep(0.1)
        x.append(message)
    logger.start(sink, format='{message}', enqueue=True)
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

def test_catch():
    def sink(msg):
        raise 1 / 0
    logger.start(sink, catch=False)
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

def test_file_not_delayed(tmpdir):
    file = tmpdir.join("test.log")
    logger.start(file.realpath(), format="{message}", delay=False)
    assert file.check(exists=1)
    assert file.read() == ""
    logger.debug("Not delayed")
    assert file.read() == "Not delayed\n"

def test_file_delayed(tmpdir):
    file = tmpdir.join("test.log")
    logger.start(file.realpath(), format="{message}", delay=True)
    assert file.check(exists=0)
    logger.debug("Delayed")
    assert file.read() == "Delayed\n"

def test_invalid_function_kwargs():
    def function(message, a="Y"):
        pass
    logger.start(function, b="X", catch=False)
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
    logger.start(writer, format='{message}', kw1="1", kw2="2", catch=False)
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
