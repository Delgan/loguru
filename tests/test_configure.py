import sys
import pytest
from loguru import logger


def test_sinks(capsys, tmpdir):
    file = tmpdir.join('test.log')

    sinks = [
        {'sink': file.realpath(), 'format': 'FileSink: {message}'},
        {'sink': sys.stdout, 'format': 'StdoutSink: {message}'},
    ]

    logger.configure(sinks=sinks)
    logger.debug('test')

    out, err = capsys.readouterr()

    assert file.read() == 'FileSink: test\n'
    assert out == 'StdoutSink: test\n'
    assert err == ''

def test_levels(writer):
    levels = [
        {'name': 'my_level', 'icon': 'X', 'no': 12},
        {'name': 'DEBUG', 'icon': '!'}
    ]

    logger.start(writer, format="{level.no}|{level.name}|{level.icon}|{message}")
    logger.configure(levels=levels)

    logger.log('my_level', 'test')
    logger.debug('no bug')

    assert writer.read() == ('12|my_level|X|test\n'
                             '10|DEBUG|!|no bug\n')

def test_extra(writer):
    extra = {
        'a': 1,
        'b': 9
    }

    logger.start(writer, format='{extra[a]} {extra[b]}')
    logger.configure(extra=extra)

    logger.debug("")

    assert writer.read() == "1 9\n"

def test_modifier(writer):
    def modifier(extra):
        extra["x"] = "y"

    logger.start(writer, format='{extra[x]}')
    logger.configure(modifier=modifier)

    logger.debug("")

    assert writer.read() == "y\n"

def test_dict_unpacking(writer):
    config = {
        "sinks": [{'sink': writer, 'format': '{level.no} - {extra[x]} {extra[xyz]} - {message}'}],
        "levels": [{'name': 'test', 'no': 30}],
        "extra": {'x': 1, 'y': 2, 'z': 3},
        "modifier": lambda extra: extra.update({"xyz": 123}),
    }

    logger.debug("NOPE")

    logger.configure(**config)

    logger.log('test', 'Yes!')

    assert writer.read() == "30 - 1 123 - Yes!\n"

def test_returned_ids(capsys):
    ids = logger.configure(sinks=[
        {'sink': sys.stdout, 'format': '{message}'},
        {'sink': sys.stderr, 'format': '{message}'},
    ])

    assert len(ids) == 2

    logger.debug("Test")

    out, err = capsys.readouterr()

    assert out == "Test\n"
    assert err == "Test\n"

    for i in ids:
        logger.stop(i)

    logger.debug("Nope")

    out, err = capsys.readouterr()

    assert out == ""
    assert err == ""

def test_dont_reset_by_default(writer):
    logger.configure(extra={"a": 1})
    logger.level("b", no=30)
    logger.start(writer, format="{level} {extra[a]} {message}")

    logger.configure()

    logger.log("b", "Test")

    assert writer.read() == "b 1 Test\n"

def test_reset_previous_sinks(writer):
    logger.start(writer, format="{message}")

    logger.configure(sinks=[])

    logger.debug("Test")

    assert writer.read() == ""

def test_reset_previous_extra(writer):
    logger.configure(extra={"a": 123})
    logger.start(writer, format="{extra[a]}", wrapped=False)

    logger.configure(extra={})

    with pytest.raises(KeyError):
        logger.debug("Nope")

def test_dont_reset_previous_levels(writer):
    logger.level("abc", no=30)

    logger.configure(levels=[])

    logger.start(writer, format="{level} {message}")

    logger.log("abc", "Test")

    assert writer.read() == "abc Test\n"

def test_configure_before_bind(writer):
    logger.configure(extra={"a": "default_a", "b": "default_b"})
    logger.start(writer, format="{extra[a]} {extra[b]} {message}")

    logger.debug("init")

    logger_a = logger.bind(a="A")
    logger_b = logger.bind(b="B")

    logger_a.debug("aaa")
    logger_b.debug("bbb")

    assert writer.read() == ("default_a default_b init\n"
                             "A default_b aaa\n"
                             "default_a B bbb\n")

def test_configure_after_bind(writer):
    logger_a = logger.bind(a="A")
    logger_b = logger.bind(b="B")

    logger.configure(extra={"a": "default_a", "b": "default_b"})
    logger.start(writer, format="{extra[a]} {extra[b]} {message}")

    logger.debug("init")

    logger_a.debug("aaa")
    logger_b.debug("bbb")

    assert writer.read() == ("default_a default_b init\n"
                             "A default_b aaa\n"
                             "default_a B bbb\n")

def test_configure_before_bind_modifier(writer):
    def modifier_root(extra):
        extra["a"] = 0

    def modifier_plus(extra):
        extra["a"] += 10

    def modifier_minus(extra):
        extra["a"] -= 10

    logger.configure(modifier=modifier_root)
    logger.start(writer, format="{extra[a]} {message}")

    logger.debug("X")

    logger_plus = logger.bind_modifier(modifier_plus)
    logger_minus = logger.bind_modifier(modifier_minus)

    logger_plus.debug("+")
    logger_minus.debug("-")

    assert writer.read() == ("0 X\n"
                             "10 +\n"
                             "-10 -\n")

def test_configure_after_bind_modifier(writer):
    def modifier_root(extra):
        extra["a"] = 0

    def modifier_plus(extra):
        extra["a"] += 10

    def modifier_minus(extra):
        extra["a"] -= 10

    logger_plus = logger.bind_modifier(modifier_plus)
    logger_minus = logger.bind_modifier(modifier_minus)

    logger.configure(modifier=modifier_root)
    logger.start(writer, format="{extra[a]} {message}")

    logger.debug("X")

    logger_plus.debug("+")
    logger_minus.debug("-")

    assert writer.read() == ("0 X\n"
                             "10 +\n"
                             "-10 -\n")

@pytest.mark.parametrize("modifier", [object(), 1, {"a": 1}])
def test_configure_invalid_modifier(modifier):
    with pytest.raises(ValueError):
        logger.configure(modifier=modifier)
