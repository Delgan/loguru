import pytest
import sys
from loguru import logger
import ansimarkup

def test_record(writer):
    logger.start(writer, format="{message}")

    logger.opt(record=True).debug("1")
    logger.opt(record=True).debug("2 {record[level]}")
    logger.opt(record=True).log(11, "3 {0} {a} {record[level].no}", 4, a=5)

    assert writer.read() == '1\n2 DEBUG\n3 4 5 11\n'

def test_exception_boolean(writer):
    logger.start(writer, format="{level.name}: {message}")

    try:
        1 / 0
    except:
        logger.opt(exception=True).debug("Error {0} {record}", 1, record="test")

    lines = writer.read().strip().splitlines()

    assert lines[0] == "DEBUG: Error 1 test"
    assert lines[-1] == "ZeroDivisionError: division by zero"

def test_exception_exc_info(writer):
    logger.start(writer, format="{message}")

    try:
        1 / 0
    except:
        exc_info = sys.exc_info()

    logger.opt(exception=exc_info).debug("test")

    lines = writer.read().strip().splitlines()

    assert lines[0] == "test"
    assert lines[-1] == "ZeroDivisionError: division by zero"

def test_exception_class(writer):
    logger.start(writer, format="{message}")

    try:
        1 / 0
    except:
        _, exc_class, _ = sys.exc_info()

    logger.opt(exception=exc_class).debug("test")

    lines = writer.read().strip().splitlines()

    assert lines[0] == "test"
    assert lines[-1] == "ZeroDivisionError: division by zero"

def test_lazy(writer):
    counter = 0
    def laziness():
        nonlocal counter
        counter += 1
        return counter

    logger.start(writer, level=10, format="{level.no} => {message}")

    logger.opt(lazy=True).log(10, "1: {lazy}", lazy=laziness)
    logger.opt(lazy=True).log(5, "2: {0}", laziness)

    logger.stop()

    logger.opt(lazy=True).log(20, "3: {}", laziness)

    a = logger.start(writer, level=15, format="{level.no} => {message}")
    b = logger.start(writer, level=20, format="{level.no} => {message}")

    logger.log(17, "4: {}", counter)
    logger.opt(lazy=True).log(14, "5: {lazy}", lazy=lambda: counter)

    logger.stop(a)

    logger.opt(lazy=True).log(16, "6: {0}", lambda: counter)

    logger.opt(lazy=True).info("7: {}", laziness)
    logger.debug("7: {}", counter)

    assert writer.read() == "10 => 1: 1\n17 => 4: 1\n20 => 7: 2\n"

def test_depth(writer):
    logger.start(writer, format="{function} : {message}")

    def a():
        logger.opt(depth=0).debug("Test 1")
        logger.opt(depth=1).debug("Test 2")

    a()

    logger.stop()

    assert writer.read() == "a : Test 1\ntest_depth : Test 2\n"

@pytest.mark.parametrize("colored, expected", [
    (False, "a - test - b"),
    (True, ansimarkup.parse("<red>a - <blue>test</blue> - b</red>")),
])
def test_ansi(writer, colored, expected):
    logger.start(writer, format="<red>a {message} b</red>", colored=colored)
    logger.opt(ansi=True).debug("- <blue>test</blue> -")
    assert writer.read() == expected + '\n'

def test_ansi_with_args(writer):
    logger.start(writer, format="=> {message} <=", colored=True)
    logger.opt(ansi=True).debug("the {0}test{end}", "<red>", end="</red>")
    assert writer.read() == ansimarkup.parse("=> the <red>test</red> <=") + '\n'

def test_ansi_with_level(writer):
    logger.start(writer, format="{message}", colored=True)
    logger.level("DEBUG", color="<green>")
    logger.opt(ansi=True).debug("a <level>level</level> b")
    assert writer.read() == ansimarkup.parse("a <green>level</green> b")+ '\n'

def test_keep_extra(writer):
    logger.configure({'extra': {'test': 123}})
    logger.start(writer, format='{extra[test]}')
    logger.opt().debug("")

    assert writer.read() == "123\n"

def test_before_bind(writer):
    logger.start(writer, format='{message}')
    logger.opt(record=True).bind(key="value").info("{record[level]}")
    assert writer.read() == "INFO\n"
