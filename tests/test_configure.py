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

def test_dict_unpacking(writer):
    config = {
        "sinks": [{'sink': writer, 'format': '{level.no} - {extra[x]} - {message}'}],
        "levels": [{'name': 'test', 'no': 30}],
        "extra": {'x': 1, 'y': 2, 'z': 3},
    }

    logger.debug("NOPE")

    logger.configure(**config)

    logger.log('test', 'Yes!')

    assert writer.read() == "30 - 1 - Yes!\n"

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

def test_remove_previous_sinks(writer):
    logger.start(writer, format="{message}")

    logger.configure(sinks=[])

    logger.debug("Test")

    assert writer.read() == ""

def test_remove_previous_levels(writer):
    logger.start(writer, format="{message}")
    logger.level("abc", no=30)

    logger.configure(levels=[])

    with pytest.raises(ValueError):
        logger.log("abc", "Test")

def test_remove_previous_extra(writer):
    logger2 = logger.bind(a=123)
    logger2.start(writer, format="{extra[a]}", wrapped=False)

    logger2.configure(extra={})

    with pytest.raises(KeyError):
        logger2.debug("Nope")

def test_dont_remove_unspecified(capsys):
    fmt = "{message} - {level} - {extra[a]}"
    logger.start(sys.stdout, format=fmt)

    logger.configure(extra={"a": 1})
    logger.debug("Test")

    out, err = capsys.readouterr()
    assert out == "Test - DEBUG - 1\n"
    assert err == ""

    logger.configure(levels=[{"name": "A", "no": 30}])
    logger.log("A", "Test 2")

    out, err = capsys.readouterr()
    assert out == "Test 2 - A - 1\n"
    assert err == ""

    logger.configure(sinks=[{"sink": sys.stderr, "format": fmt}])
    logger.log("A", "Test 3")

    out, err = capsys.readouterr()
    assert out == ""
    assert err == "Test 3 - A - 1\n"
