import pytest
from loguru import logger


@pytest.mark.parametrize(
    "message, format, expected",
    [
        ("a", "Message: {message}", "Message: a\n"),
        ("b", "Nope", "Nope\n"),
        ("c", "{level} {message} {level}", "DEBUG c DEBUG\n"),
        ("d", "{message} {level} {level.no} {level.name}", "d DEBUG 10 DEBUG\n"),
        ("e", lambda _: "{message}", "e"),
        ("f", lambda r: "{message} " + r["level"].name, "f DEBUG"),
    ],
)
def test_format(message, format, expected, writer):
    logger.add(writer, format=format)
    logger.debug(message)
    assert writer.read() == expected


def test_progressive_format(writer):
    def formatter(record):
        fmt = "[{level.name}] {message}"
        if "noend" not in record["extra"]:
            fmt += "\n"
        return fmt

    logger.add(writer, format=formatter)
    logger.bind(noend=True).debug("Start: ")
    for _ in range(5):
        logger.opt(raw=True).debug(".")
    logger.opt(raw=True).debug("\n")
    logger.debug("End")
    assert writer.read() == ("[DEBUG] Start: .....\n" "[DEBUG] End\n")


def test_function_format_without_exception(writer):
    logger.add(writer, format=lambda _: "{message}\n")
    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("Error!")
    assert writer.read() == "Error!\n"


def test_function_format_with_exception(writer):
    logger.add(writer, format=lambda _: "{message}\n{exception}")
    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("Error!")
    lines = writer.read().splitlines()
    assert lines[0] == "Error!"
    assert lines[-1] == "ZeroDivisionError: division by zero"


@pytest.mark.parametrize("format", [-1, 3.4, object()])
def test_invalid_format(writer, format):
    with pytest.raises(ValueError):
        logger.add(writer, format=format)
