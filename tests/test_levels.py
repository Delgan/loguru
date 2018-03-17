import pytest
import ansimarkup
from loguru import logger

am = ansimarkup.AnsiMarkup(tags={"empty": ansimarkup.parse("")})

def test_log_int_level(writer):
    logger.start(writer, format='{level.name} -> {level.no} -> {message}', colored=False)
    logger.log(10, "test")

    assert writer.read() == "Level 10 -> 10 -> test\n"

def test_log_str_level(writer):
    logger.start(writer, format='{level.name} -> {level.no} -> {message}', colored=False)
    logger.log("DEBUG", "test")

    assert writer.read() == "DEBUG -> 10 -> test\n"

def test_add_level(writer):
    name = "L3V3L"
    icon = "[o]"
    level = 10

    logger.level(name, level, color="<red>", icon=icon)
    logger.start(writer, format='{level.icon} <level>{level.name}</level> -> {level.no} -> {message}', colored=True)

    logger.log(name, "test")
    expected = am.parse("%s <red>%s</red> -> %d -> test" % (icon, name, level))
    assert writer.read() == expected + '\n'

@pytest.mark.parametrize('colored, expected', [
    (False, "foo | 10 | a"),
    (True, am.parse("<red>foo | 10 | a</red>"))
])
def test_add_level_after_start(writer, colored, expected):
    logger.start(writer, level="DEBUG", format='<level>{level.name} | {level.no} | {message}</level>', colored=colored)
    logger.level("foo", 10, color="<red>")
    logger.log("foo", "a")
    assert writer.read() == expected + "\n"

def test_add_level_then_log_with_int_value(writer):
    logger.level("foo", 16)
    logger.start(writer, level="foo", format="{level.name} {level.no} {message}", colored=False)

    logger.log(16, "test")

    assert writer.read() == "Level 16 16 test\n"

def test_add_malicious_level(writer):
    name = "Level 15"

    logger.level(name, 45, color="<red>")
    logger.start(writer, format='{level.name} & {level.no} & <level>{message}</level>', colored=True)

    logger.log(15, ' A ')
    logger.log(name, ' B ')

    assert writer.read() == (am.parse('Level 15 & 15 & <empty> A </empty>') + '\n' +
                             am.parse('Level 15 & 45 & <red> B </red>') + '\n')

def test_add_existing_level(writer):
    logger.level("INFO", 45, color="<red>")
    logger.start(writer, format='{level.icon} + <level>{level.name}</level> + {level.no} = {message}', colored=True)

    logger.info("a")
    logger.log("INFO", "b")
    logger.log(10, "c")
    logger.log(45, "d")

    assert writer.read() == (am.parse('ℹ️ + <red>INFO</red> + 45 = a') + '\n' +
                             am.parse('ℹ️ + <red>INFO</red> + 45 = b') + '\n' +
                             am.parse('  + <empty>Level 10</empty> + 10 = c') + '\n' +
                             am.parse('  + <empty>Level 45</empty> + 45 = d') + '\n')

def test_edit_level(writer):
    logger.level("info", no=0, color="<bold>", icon="[?]")
    logger.start(writer, format="<level>->{level.no}, {level.name}, {level.icon}, {message}<-</level>", colored=True)

    logger.log("info", "nope")

    logger.level("info", no=11)
    logger.log("info", "a")

    logger.level("info", icon="[!]")
    logger.log("info", "b")

    logger.level("info", color="<red>")
    logger.log("info", "c")

    assert writer.read() == (ansimarkup.parse("<bold>->11, info, [?], a<-</bold>") + "\n" +
                             ansimarkup.parse("<bold>->11, info, [!], b<-</bold>") + "\n" +
                             ansimarkup.parse("<red>->11, info, [!], c<-</red>") + "\n")

def test_edit_existing_level(writer):
    logger.level("DEBUG", no=20, icon="!")
    logger.start(writer, format="{level.no}, <level>{level.name}</level>, {level.icon}, {message}", colored=False)
    logger.debug("a")
    assert writer.read() == "20, DEBUG, !, a\n"

def test_get_level():
    level = (11, "<red>", "[!]")
    logger.level("lvl", *level)
    assert logger.level("lvl") == level

def test_get_existing_level():
    assert logger.level("DEBUG") == (10, "<blue><bold>", "🐞")

def test_start_custom_level(writer):
    logger.level("foo", 17, color="<yellow>")
    logger.start(writer, level="foo", format='<level>{level.name} + {level.no} + {message}</level>', colored=False)

    logger.debug("nope")
    logger.info("yes")

    assert writer.read() == 'INFO + 20 + yes\n'

def test_updating_min_level(writer):
    logger.debug("Early exit -> no {error}", nope=None)

    a = logger.start(writer, level="DEBUG")

    with pytest.raises(KeyError):
        logger.debug("An {error} will occur!", nope=None)

    logger.trace("Early exit -> no {error}", nope=None)

    logger.start(writer, level="INFO")
    logger.stop(a)

    logger.debug("Early exit -> no {error}", nope=None)

@pytest.mark.parametrize("level", ["foo", -1, 3.4, object()])
def test_log_invalid_level(writer, level):
    logger.start(writer)
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
