import pytest

use_binded = pytest.mark.parametrize("use_binded", [True, False])

def test_binding(logger, writer):
    logger.start(writer, format="{extra[a]} + {extra[b]}")
    logger.extra = {"a": 0, "b": 0}
    logger.debug("")
    logger.bind(a=1)
    logger.debug("")
    logger = logger.bind(a=2)
    logger.debug("")
    logger2 = logger.bind(b=3)
    logger2.debug("")
    logger.debug("")
    logger2.bind(a=10, b=10).debug("")

    assert writer.read() == (
        "0 + 0\n"
        "0 + 0\n"
        "2 + 0\n"
        "2 + 3\n"
        "2 + 0\n"
        "10 + 10\n"
    )

@use_binded
def test_start_and_bind(logger, writer, use_binded):
    logger2 = logger.bind()

    log = logger2 if use_binded else logger

    log.start(writer, format="{message}")

    logger.debug("?")
    logger2.debug("!")
    assert writer.read() == "?\n!\n"

@use_binded
def test_add_level_and_bind(logger, writer, use_binded):
    logger2 = logger.bind()

    log = logger2 if use_binded else logger

    log.start(writer, format="{level.name} {message}")
    log.add_level("bar", 15)

    logger.log("bar", "?")
    logger2.log("bar", "!")
    assert writer.read() == "bar ?\nbar !\n"
