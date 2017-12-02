import pytest
import sys

def test_record(logger, writer):
    logger.start(writer, format="{message}")

    logger.opt(record=True).debug("1")
    logger.opt(record=True).debug("2 {record[level]}")
    logger.opt(record=True).log(11, "3 {0} {a} {record[level].no}", 4, a=5)

    assert writer.read() == '1\n2 DEBUG\n3 4 5 11\n'

def test_exception_boolean(logger, writer):
    logger.start(writer, format="{level.name}: {message}")

    try:
        1 / 0
    except:
        logger.opt(exception=True).debug("Error {0} {record}", 1, record="test")

    lines = writer.read().strip().splitlines()

    assert lines[0] == "DEBUG: Error 1 test"
    assert lines[-1] == "ZeroDivisionError: division by zero"

def test_exception_exc_info(logger, writer):
    logger.start(writer, format="{message}")

    try:
        1 / 0
    except:
        exc_info = sys.exc_info()

    logger.opt(exception=exc_info).debug("test")

    lines = writer.read().strip().splitlines()

    assert lines[0] == "test"
    assert lines[-1] == "ZeroDivisionError: division by zero"

def test_exception_class(logger, writer):
    logger.start(writer, format="{message}")

    try:
        1 / 0
    except:
        _, exc_class, _ = sys.exc_info()

    logger.opt(exception=exc_class).debug("test")

    lines = writer.read().strip().splitlines()

    assert lines[0] == "test"
    assert lines[-1] == "ZeroDivisionError: division by zero"

def test_lazy(logger, writer):
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

def test_keep_extra(logger, writer):
    logger.extra['test'] = 123
    logger.start(writer, format='{extra[test]}')
    logger.opt().debug("")

    assert writer.read() == "123\n"

def test_keep_others(logger, writer):
    logger.start(writer, format='{message}')
    logger.opt(record=True).opt().debug("{record[level].name}")
    logger.debug("{record}", record=123)
    try:
        1 / 0
    except:
        logger.opt(record=True).opt(exception=True).debug("{record[level].no}")

    result = writer.read().strip()
    assert result.startswith("DEBUG\n123\n10\n")
    assert result.endswith("ZeroDivisionError: division by zero")

def test_before_bind(logger, writer):
    logger.start(writer, format='{message}')
    logger.opt(record=True).bind(key="value").info("{record[level]}")
    assert writer.read() == "INFO\n"
