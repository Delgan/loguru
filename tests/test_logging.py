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

@pytest.mark.parametrize('existing', [True, False])
def test_log_custom_level(logger, writer, existing):
    if existing:
        name, no = 'DEBUG', 10
    else:
        name, no = 'UNKNOWN', 11

    logger.log_to(writer, format='{level.name} -> {level.no} -> {message}', colored=False)
    logger.log(no, "test")

    assert writer.read() == "%s -> %d -> test\n" % (name, no)

@pytest.mark.parametrize('set_level_first', [True, False])
@pytest.mark.parametrize('existing', [True, False])
@pytest.mark.parametrize('custom_color', [True, False])
def test_set_level_new(logger, writer, set_level_first, existing, custom_color):
    name = "L3V3L"
    colored_name = ("\x1b[31m%s\x1b[0m" % name) if custom_color else name

    if existing:
        level = 10
    else:
        level = 11

    def set_level():
        logger.set_level(level, name, "<red>" if custom_color else "")

    def log_to():
        logger.log_to(writer, format='<level>{level.name}</level> -> {level.no} -> {message}', colored=custom_color)

    if set_level_first:
        set_level()
        log_to()
    else:
        log_to()
        set_level()

    if existing:
        logger.debug("test")
    else:
        logger.log(level, "test")

    assert writer.read() == "%s -> %d -> test\n" % (colored_name, level)

@pytest.mark.parametrize("level", ["100", object(), {}])
def test_invalid_level_value(logger, level):
    with pytest.raises(ValueError):
        logger.set_level(level, "TEST")

@pytest.mark.parametrize("name", [100, object(), {}])
def test_invalid_level_name(logger, name):
    with pytest.raises(ValueError):
        logger.set_level(25, name)
