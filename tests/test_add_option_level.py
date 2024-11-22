import pytest

from loguru import logger


@pytest.mark.parametrize("level", [0, "TRACE", "INFO", 20])
def test_level_low_enough(writer, level):
    logger.add(writer, level=level, format="{message}")
    logger.info("Test level")
    assert writer.read() == "Test level\n"


@pytest.mark.parametrize("level", ["WARNING", 25])
def test_level_too_high(writer, level):
    logger.add(writer, level=level, format="{message}")
    logger.info("Test level")
    assert writer.read() == ""


@pytest.mark.parametrize("level", [3.4, object()])
def test_invalid_level_type(writer, level):
    with pytest.raises(TypeError):
        logger.add(writer, level=level)


def test_invalid_level_value(writer):
    with pytest.raises(
        ValueError, match="^Invalid level value, it should be a positive integer, not: -1$"
    ):
        logger.add(writer, level=-1)


def test_unknown_level(writer):
    with pytest.raises(ValueError, match="^Level 'foo' does not exist$"):
        logger.add(writer, level="foo")
