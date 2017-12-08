import sys
from loguru import logger


class StrAttr(str):
    pass

def test_existing_level(writer):
    logger.start(writer, format="<level>{message}</level>", colored=True)

    level = StrAttr("INFO")
    level.name, level.no, level.icon = "INFO", 20, "!"
    record = {
        "level": level,
        "message": " test ",
    }

    logger.handle(record)
    assert writer.read() == "\x1b[1m test \x1b[0m\n"

def test_not_existing_level(writer):
    logger.start(writer, format="<level>{message}</level>", colored=True)

    level = StrAttr("FOOBAR")
    level.name, level.no, level.icon = "FOOBAR", 20, "!"
    record = {
        "level": level,
        "message": " test ",
    }

    logger.handle(record)
    assert writer.read() == " test \x1b[0m\n"

def test_exception(writer):
    logger.start(writer, format="{message}")

    try:
        1 / 0
    except ZeroDivisionError:
        exception = sys.exc_info()

    level = StrAttr("INFO")
    level.name, level.no = "ERROR", 40
    record = dict(message="Test", level=level)

    logger.handle(record, exception=exception)

    lines = writer.read().strip().splitlines()
    assert lines[0] == "Test"
    assert lines[-1] == "ZeroDivisionError: division by zero"
    assert sum(line.startswith("> ") for line in lines) == 1
