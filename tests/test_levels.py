import loguru
import pytest


def test_log_int_level(logger, writer):
    logger.start(writer, format='{level.name} -> {level.no} -> {message}', colored=False)
    logger.log(10, "test")

    assert writer.read() == "Level 10 -> 10 -> test\n"

def test_log_str_level(logger, writer):
    logger.start(writer, format='{level.name} -> {level.no} -> {message}', colored=False)
    logger.log("DEBUG", "test")

    assert writer.read() == "DEBUG -> 10 -> test\n"

def test_add_level(logger, writer):
    name = "L3V3L"
    icon = "[o]"
    level = 10

    logger.level(name, level, color="<red>", icon=icon)
    logger.start(writer, format='{level.icon} <level>{level.name}</level> -> {level.no} -> {message}', colored=True)

    logger.log(name, "test")
    assert writer.read() == "%s \x1b[31m%s\x1b[0m -> %d -> test\n" % (icon, name, level)

@pytest.mark.parametrize('colored', [True, False])
def test_add_level_after_start(logger, writer, colored):
    logger.start(writer, level="DEBUG", format='<level>{level.name} | {level.no} | {message}</level>', colored=colored)
    logger.level("foo", 10, color="<red>")

    logger.log("foo", "a")

    expected = "foo | 10 | a"
    if colored:
        expected = "\x1b[31m%s\x1b[0m" % expected

    assert writer.read() == expected + "\n"

def test_add_level_then_log_with_int_value(logger, writer):
    logger.level("foo", 16)
    logger.start(writer, level="foo", format="{level.name} {level.no} {message}", colored=False)

    logger.log(16, "test")

    assert writer.read() == "Level 16 16 test\n"

def test_add_malicious_level(logger, writer):
    name = "Level 15"

    logger.level(name, 45, color="<red>")
    logger.start(writer, format='{level.name} & {level.no} & <level>{message}</level>', colored=True)

    logger.log(15, ' A ')
    logger.log(name, ' B ')

    assert writer.read() == ('Level 15 & 15 &  A \x1b[0m\n'
                             'Level 15 & 45 & \x1b[31m B \x1b[0m\n')

def test_add_existing_level(logger, writer):
    logger.level("INFO", 45, color="<red>")
    logger.start(writer, format='{level.icon} + <level>{level.name}</level> + {level.no} = {message}', colored=True)

    logger.info("a")
    logger.log("INFO", "b")
    logger.log(10, "c")
    logger.log(45, "d")

    assert writer.read() == ('ℹ️ + \x1b[31mINFO\x1b[0m + 45 = a\n'
                             'ℹ️ + \x1b[31mINFO\x1b[0m + 45 = b\n'
                             '  + Level 10\x1b[0m + 10 = c\n'
                             '  + Level 45\x1b[0m + 45 = d\n')

def test_edit_level(logger, writer):
    logger.level("info", no=0, color="<bold>", icon="[?]")
    logger.start(writer, format="<level>->{level.no}, {level.name}, {level.icon}, {message}<-</level>", colored=True)

    logger.log("info", "nope")

    logger.level("info", no=11)
    logger.log("info", "a")

    logger.level("info", icon="[!]")
    logger.log("info", "b")

    logger.level("info", color="<red>")
    logger.log("info", "c")

    assert writer.read() == ("\x1b[1m->11, info, [?], a<-\x1b[0m\n"
                             "\x1b[1m->11, info, [!], b<-\x1b[0m\n"
                             "\x1b[31m->11, info, [!], c<-\x1b[0m\n")

def test_edit_existing_level(logger, writer):
    logger.level("DEBUG", no=20, icon="!")
    logger.start(writer, format="{level.no}, <level>{level.name}</level>, {level.icon}, {message}", colored=False)
    logger.debug("a")
    assert writer.read() == "20, DEBUG, !, a\n"

def test_get_level(logger):
    level = (11, "<red>", "[!]")
    logger.level("lvl", *level)
    assert logger.level("lvl") == level

def test_get_existing_level(logger):
    assert logger.level("DEBUG") == (10, "<blue><bold>", "🐞")

def test_start_custom_level(logger, writer):
    logger.level("foo", 17, color="<yellow>")
    logger.start(writer, level="foo", format='<level>{level.name} + {level.no} + {message}</level>', colored=False)

    logger.debug("nope")
    logger.info("yes")

    assert writer.read() == 'INFO + 20 + yes\n'

@pytest.mark.parametrize("level", ["foo", -1, 3.4, object()])
def test_log_invalid_level(logger, level):
    with pytest.raises(ValueError):
        logger.log(level, "test")

@pytest.mark.parametrize("level_name", [10, object()])
def test_add_invalid_level_name(logger, level_name):
    with pytest.raises(ValueError):
        logger.level(level_name, 11)

@pytest.mark.parametrize("level_value", ["1", -1, 3.4, object()])
def test_add_invalid_level_value(logger, level_value):
    with pytest.raises(ValueError):
        logger.level("test", level_value)

@pytest.mark.parametrize("level", ["foo", 10, object()])
def test_get_invalid_level(logger, level):
    with pytest.raises(ValueError):
        logger.level(level)

@pytest.mark.parametrize("level", ["foo", 10, object()])
def test_edit_invalid_level(logger, level):
    with pytest.raises(ValueError):
        logger.level(level, icon="?")
