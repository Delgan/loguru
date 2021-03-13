import functools

import pytest

from loguru import logger

from .conftest import parse


def test_log_int_level(writer):
    logger.add(writer, format="{level.name} -> {level.no} -> {message}", colorize=False)
    logger.log(10, "test")

    assert writer.read() == "Level 10 -> 10 -> test\n"


def test_log_str_level(writer):
    logger.add(writer, format="{level.name} -> {level.no} -> {message}", colorize=False)
    logger.log("DEBUG", "test")

    assert writer.read() == "DEBUG -> 10 -> test\n"


def test_add_level(writer):
    name = "L3V3L"
    icon = "[o]"
    level = 10

    logger.level(name, level, color="<red>", icon=icon)
    fmt = "{level.icon} <level>{level.name}</level> -> {level.no} -> {message}"
    logger.add(writer, format=fmt, colorize=True)

    logger.log(name, "test")
    expected = parse("%s <red>%s</red> -> %d -> test" % (icon, name, level))
    assert writer.read() == expected + "\n"


@pytest.mark.parametrize(
    "colorize, expected", [(False, "foo | 10 | a"), (True, parse("<red>foo | 10 | a</red>"))]
)
def test_add_level_after_add(writer, colorize, expected):
    fmt = "<level>{level.name} | {level.no} | {message}</level>"
    logger.add(writer, level="DEBUG", format=fmt, colorize=colorize)
    logger.level("foo", 10, color="<red>")
    logger.log("foo", "a")
    assert writer.read() == expected + "\n"


def test_add_level_then_log_with_int_value(writer):
    logger.level("foo", 16)
    logger.add(writer, level="foo", format="{level.name} {level.no} {message}", colorize=False)

    logger.log(16, "test")

    assert writer.read() == "Level 16 16 test\n"


def test_add_malicious_level(writer):
    name = "Level 15"

    logger.level(name, 45, color="<red>")
    fmt = "{level.name} & {level.no} & <level>{message}</level>"
    logger.add(writer, format=fmt, colorize=True)

    logger.log(15, " A ")
    logger.log(name, " B ")

    assert writer.read() == parse("Level 15 & 15 &  A \x1b[0m\nLevel 15 & 45 & <red> B </red>\n")


def test_add_existing_level(writer):
    logger.level("INFO", color="<red>")
    fmt = "{level.icon} + <level>{level.name}</level> + {level.no} = {message}"
    logger.add(writer, format=fmt, colorize=True)

    logger.info("a")
    logger.log("INFO", "b")
    logger.log(10, "c")
    logger.log(20, "d")

    assert writer.read() == parse(
        "ℹ️ + <red>INFO</red> + 20 = a\n"
        "ℹ️ + <red>INFO</red> + 20 = b\n"
        "  + Level 10\x1b[0m + 10 = c\n"
        "  + Level 20\x1b[0m + 20 = d\n"
    )


def test_blank_color(writer):
    logger.level("INFO", color=" ")
    logger.add(writer, level="DEBUG", format="<level>{message}</level>", colorize=True)
    logger.info("Test")
    assert writer.read() == parse("Test" "\x1b[0m" "\n")


def test_edit_level(writer):
    logger.level("info", no=11, color="<bold>", icon="[?]")
    fmt = "<level>->{level.no}, {level.name}, {level.icon}, {message}<-</level>"
    logger.add(writer, format=fmt, colorize=True)

    logger.log("info", "a")

    logger.level("info", icon="[!]")
    logger.log("info", "b")

    logger.level("info", color="<red>")
    logger.log("info", "c")

    assert writer.read() == parse(
        "<bold>->11, info, [?], a<-</bold>\n"
        "<bold>->11, info, [!], b<-</bold>\n"
        "<red>->11, info, [!], c<-</red>\n"
    )


def test_edit_existing_level(writer):
    logger.level("DEBUG", icon="!")
    fmt = "{level.no}, <level>{level.name}</level>, {level.icon}, {message}"
    logger.add(writer, format=fmt, colorize=False)
    logger.debug("a")
    assert writer.read() == "10, DEBUG, !, a\n"


def test_get_level():
    level = ("lvl", 11, "<red>", "[!]")
    logger.level(*level)
    assert logger.level("lvl") == level


def test_get_existing_level():
    assert logger.level("DEBUG") == ("DEBUG", 10, "<blue><bold>", "🐞")


def test_add_custom_level(writer):
    logger.level("foo", 17, color="<yellow>")
    logger.add(
        writer,
        level="foo",
        format="<level>{level.name} + {level.no} + {message}</level>",
        colorize=False,
    )

    logger.debug("nope")
    logger.info("yes")

    assert writer.read() == "INFO + 20 + yes\n"


def test_updating_min_level(writer):
    logger.debug("Early exit -> no {error}", nope=None)

    a = logger.add(writer, level="DEBUG")

    with pytest.raises(KeyError):
        logger.debug("An {error} will occur!", nope=None)

    logger.trace("Early exit -> no {error}", nope=None)

    logger.add(writer, level="INFO")
    logger.remove(a)

    logger.debug("Early exit -> no {error}", nope=None)


def test_assign_custom_level_method(writer):
    logger.level("foobar", no=33, icon="🤖", color="<blue>")

    logger.__class__.foobar = functools.partialmethod(logger.__class__.log, "foobar")
    logger.foobar("Message not logged")
    logger.add(
        writer,
        format="<lvl>{level.name} {level.no} {level.icon} {message} {extra}</lvl>",
        colorize=True,
    )
    logger.foobar("Logged message")
    logger.bind(something="otherthing").foobar("Another message")
    assert writer.read() == parse(
        "<blue>foobar 33 🤖 Logged message {}</blue>\n"
        "<blue>foobar 33 🤖 Another message {'something': 'otherthing'}</blue>\n"
    )


def test_updating_level_no_not_allowed():
    with pytest.raises(TypeError, match=r".*can't update its severity"):
        logger.level("DEBUG", 100)


@pytest.mark.parametrize("level", [3.4, object()])
def test_log_invalid_level(writer, level):
    logger.add(writer)
    with pytest.raises(TypeError):
        logger.log(level, "test")


@pytest.mark.parametrize("level", ["foo", "debug", -1])
def test_log_unknown_level(writer, level):
    logger.add(writer)
    with pytest.raises(ValueError):
        logger.log(level, "test")


@pytest.mark.parametrize("level_name", [10, object()])
def test_add_invalid_level_name(level_name):
    with pytest.raises(TypeError):
        logger.level(level_name, 11)


@pytest.mark.parametrize("level_value", ["1", object(), 3.4])
def test_add_invalid_level_type(level_value):
    with pytest.raises(TypeError):
        logger.level("test", level_value)


def test_add_invalid_level_value():
    with pytest.raises(ValueError):
        logger.level("test", -1)


@pytest.mark.parametrize("level", [10, object()])
def test_get_invalid_level(level):
    with pytest.raises(TypeError):
        logger.level(level)


def test_get_unknown_level():
    with pytest.raises(ValueError):
        logger.level("foo")


@pytest.mark.parametrize("level", [10, object()])
def test_edit_invalid_level(level):
    with pytest.raises(TypeError):
        logger.level(level, icon="?")


def test_edit_unknown_level():
    with pytest.raises(ValueError):
        logger.level("foo", icon="?")


@pytest.mark.parametrize("color", ["</>", "<foo>", "</red>", "<lvl>", " <level> "])
def test_add_invalid_level_color(color):
    with pytest.raises(ValueError):
        logger.level("foobar", no=20, icon="", color=color)
