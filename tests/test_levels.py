import pytest
import ansimarkup
from loguru import logger

am = ansimarkup.AnsiMarkup(tags={"empty": ansimarkup.parse("")})


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
    expected = am.parse("%s <red>%s</red> -> %d -> test" % (icon, name, level))
    assert writer.read() == expected + "\n"


@pytest.mark.parametrize(
    "colorize, expected", [(False, "foo | 10 | a"), (True, am.parse("<red>foo | 10 | a</red>"))]
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

    res = am.parse("Level 15 & 15 & <empty> A </empty>\n" "Level 15 & 45 & <red> B </red>\n")
    assert writer.read() == res


def test_add_existing_level(writer):
    logger.level("INFO", 45, color="<red>")
    fmt = "{level.icon} + <level>{level.name}</level> + {level.no} = {message}"
    logger.add(writer, format=fmt, colorize=True)

    logger.info("a")
    logger.log("INFO", "b")
    logger.log(10, "c")
    logger.log(45, "d")

    assert writer.read() == am.parse(
        "ℹ️ + <red>INFO</red> + 45 = a\n"
        "ℹ️ + <red>INFO</red> + 45 = b\n"
        "  + <empty>Level 10</empty> + 10 = c\n"
        "  + <empty>Level 45</empty> + 45 = d\n"
    )


def test_blank_color(writer):
    logger.level("INFO", color=" ")
    logger.add(writer, level="DEBUG", format="<level>{message}</level>", colorize=True)
    logger.info("Test")
    assert writer.read() == am.parse("<empty>Test</empty>\n")


def test_edit_level(writer):
    logger.level("info", no=0, color="<bold>", icon="[?]")
    fmt = "<level>->{level.no}, {level.name}, {level.icon}, {message}<-</level>"
    logger.add(writer, format=fmt, colorize=True)

    logger.log("info", "nope")

    logger.level("info", no=11)
    logger.log("info", "a")

    logger.level("info", icon="[!]")
    logger.log("info", "b")

    logger.level("info", color="<red>")
    logger.log("info", "c")

    assert writer.read() == ansimarkup.parse(
        "<bold>->11, info, [?], a<-</bold>\n"
        "<bold>->11, info, [!], b<-</bold>\n"
        "<red>->11, info, [!], c<-</red>\n"
    )


def test_edit_existing_level(writer):
    logger.level("DEBUG", no=20, icon="!")
    fmt = "{level.no}, <level>{level.name}</level>, {level.icon}, {message}"
    logger.add(writer, format=fmt, colorize=False)
    logger.debug("a")
    assert writer.read() == "20, DEBUG, !, a\n"


def test_get_level():
    level = (11, "<red>", "[!]")
    logger.level("lvl", *level)
    assert logger.level("lvl") == level


def test_get_existing_level():
    assert logger.level("DEBUG") == (10, "<blue><bold>", "🐞")


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


@pytest.mark.parametrize("level", ["foo", -1, 3.4, object()])
def test_log_invalid_level(writer, level):
    logger.add(writer)
    with pytest.raises(ValueError):
        logger.log(level, "test")


@pytest.mark.parametrize("level_name", [10, object()])
def test_add_invalid_level_name(level_name):
    with pytest.raises(ValueError):
        logger.level(level_name, 11)


@pytest.mark.parametrize("level_value", ["1", -1, 3.4, object()])
def test_add_invalid_level_value(level_value):
    with pytest.raises(ValueError):
        logger.level("test", level_value)


@pytest.mark.parametrize("level", ["foo", 10, object()])
def test_get_invalid_level(level):
    with pytest.raises(ValueError):
        logger.level(level)


@pytest.mark.parametrize("level", ["foo", 10, object()])
def test_edit_invalid_level(level):
    with pytest.raises(ValueError):
        logger.level(level, icon="?")
