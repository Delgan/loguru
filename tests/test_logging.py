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
        name, no = 'Level 11', 11

    logger.log_to(writer, format='{level.name} -> {level.no} -> {message}', colored=False)
    logger.log(no, "test")

    assert writer.read() == "%s -> %d -> test\n" % (name, no)

@pytest.mark.parametrize('add_level_first', [True, False])
@pytest.mark.parametrize('existing', [True, False])
@pytest.mark.parametrize('custom_color', [True, False])
def test_add_level_new(logger, writer, add_level_first, existing, custom_color):
    name = "L3V3L"
    colored_name = ("\x1b[31m%s\x1b[0m" % name) if custom_color else name

    if existing:
        level = 10
    else:
        level = 11

    def add_level():
        logger.add_level(level, name, "<red>" if custom_color else "")

    def log_to():
        logger.log_to(writer, format='<level>{level.name}</level> -> {level.no} -> {message}', colored=custom_color)

    if add_level_first:
        add_level()
        log_to()
    else:
        log_to()
        add_level()

    if existing:
        logger.debug("test")
    else:
        logger.log(level, "test")

    assert writer.read() == "%s -> %d -> test\n" % (colored_name, level)

@pytest.mark.parametrize('custom_level', [True, False])
def test_log_to_string_level(logger, writer, custom_level):
    if custom_level:
        level = 'foo'
        logger.add_level(20, level)
    else:
        level = 'info'

    logger.log_to(writer, level=level, format='{level.name} + {level.no} + {message}')
    logger.debug("nope")
    logger.info("yes")
    assert writer.read() == '%s + 20 + yes\n' % level.upper()

@pytest.mark.parametrize('custom_level', [True, False])
def test_log_function_string_level(logger, writer, custom_level):
    if custom_level:
        level = 'FOO'
        logger.add_level(20, level)
    else:
        level = 'INFO'

    logger.log_to(writer, format='{level.name} + {level.no} + {message}')
    logger.log(level, 'test')
    assert writer.read() == '%s + 20 + test\n' % level.upper()

@pytest.mark.parametrize('func', ['log_to', 'log'])
def test_not_existing_level(logger, writer, func):
    with pytest.raises(KeyError):
        if func == 'log_to':
            logger.log_to(writer, level="NOPE")
        elif func == 'log':
            logger.log("NOPE", "test")

@pytest.mark.parametrize("level", ["100", object(), {}])
def test_invalid_level_value(logger, level):
    with pytest.raises(ValueError):
        logger.add_level(level, "TEST")

@pytest.mark.parametrize("name", [100, object(), {}])
def test_invalid_level_name(logger, name):
    with pytest.raises(ValueError):
        logger.add_level(25, name)
