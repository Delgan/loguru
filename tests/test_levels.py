import loguru
import pytest


@pytest.mark.parametrize('message, args, kwargs', [
    ('{} + {} = {}', [1, 2, 3], {}),
    ('{one} + {two} = {three}', [], dict(one=1, two=2, three=3)),
    ('{0} + {two} = {1}', [1, 3], dict(two=2, nope=4)),
])
@pytest.mark.parametrize('use_log_function', [False, True])
def test_basic_logging(logger, writer, message, args, kwargs, use_log_function):
    logger.log_to(writer, format='{message}', colored=False)

    if use_log_function:
        logger.log(10, message, *args, **kwargs)
    else:
        logger.debug(message, *args, **kwargs)

    assert writer.read() == '1 + 2 = 3\n'

def test_log_int_level(logger, writer):
    logger.log_to(writer, format='{level.name} -> {level.no} -> {message}', colored=False)
    logger.log(10, "test")

    assert writer.read() == "Level 10 -> 10 -> test\n"

@pytest.mark.parametrize('lower', [True, False])
def test_log_str_level(logger, writer, lower):
    logger.log_to(writer, format='{level.name} -> {level.no} -> {message}', colored=False)
    logger.log("debug" if lower else "DEBUG", "test")

    assert writer.read() == "DEBUG -> 10 -> test\n"

def test_add_level(logger, writer):
    name = "L3V3L"
    icon = "[o]"
    level = 10

    logger.add_level(name.lower(), level, color="<red>", icon=icon)
    logger.log_to(writer, format='{level.icon} <level>{level.name}</level> -> {level.no} -> {message}', colored=True)

    logger.log(name, "test")
    assert writer.read() == "%s \x1b[31m%s\x1b[0m -> %d -> test\n" % (icon, name, level)

@pytest.mark.parametrize('colored', [True, False])
def test_add_level_after_log_to(logger, writer, colored):
    logger.log_to(writer, level="debug", format='<level>{level.name} | {level.no} | {message}</level>', colored=colored)
    logger.add_level("foo", 10, color="<red>")

    logger.log("foo", "a")

    expected = "FOO | 10 | a"
    if colored:
        expected = "\x1b[31m%s\x1b[0m" % expected

    assert writer.read() == expected + "\n"

def test_add_level_then_log_with_int_value(logger, writer):
    logger.add_level("foo", 16)
    logger.log_to(writer, level="foo", format="{level.name} {level.no} {message}", colored=False)

    logger.log(16, "test")

    assert writer.read() == "Level 16 16 test\n"

def test_add_malicious_level(logger, writer):
    name = "Level 15"

    logger.add_level(name, 45, color="<red>")
    logger.log_to(writer, format='{level.name} & {level.no} & <level>{message}</level>', colored=True)

    logger.log(15, ' A ')
    logger.log(name, ' B ')

    assert writer.read() == ('Level 15 & 15 &  A \x1b[0m\n'
                             'LEVEL 15 & 45 & \x1b[31m B \x1b[0m\n')

def test_add_existing_level(logger, writer):
    logger.add_level("info", 45, color="<red>")
    logger.log_to(writer, format='{level.icon} + <level>{level.name}</level> + {level.no} = {message}', colored=True)

    logger.info("a")
    logger.log("info", "b")
    logger.log(10, "c")
    logger.log(45, "d")

    assert writer.read() == ('  + \x1b[31mINFO\x1b[0m + 45 = a\n'
                             '  + \x1b[31mINFO\x1b[0m + 45 = b\n'
                             '  + Level 10\x1b[0m + 10 = c\n'
                             '  + Level 45\x1b[0m + 45 = d\n')

@pytest.mark.parametrize('level', ['foo', 'FOO', 17])
def test_log_to_custom_level(logger, writer, level):
    logger.add_level("foo", 17, color="<yellow>")
    logger.log_to(writer, level=level, format='<level>{level.name} + {level.no} + {message}</level>', colored=False)

    logger.debug("nope")
    logger.info("yes")

    assert writer.read() == 'INFO + 20 + yes\n'

def test_log_invalid_level_name(logger, writer):
    with pytest.raises(KeyError):
        logger.log("foo", "test")

def test_log_to_invalid_level_name(logger, writer):
    with pytest.raises(KeyError):
        logger.log_to(writer, level="FOO")

@pytest.mark.parametrize("level", ["100", object(), {}])
def test_add_level_invalid_value(logger, level):
    with pytest.raises(ValueError):
        logger.add_level(level, "TEST")

@pytest.mark.parametrize("name", [100, object(), {}])
def test_add_level_invalid_name(logger, name):
    with pytest.raises(ValueError):
        logger.add_level(25, name)
