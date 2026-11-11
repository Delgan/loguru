from loguru import logger


def test_sanitize_disabled_by_default(writer):
    logger.add(writer, format="{message}", colorize=False)
    logger.info("\x1b[2J")
    assert writer.read() == "\x1b[2J\n"


def test_sanitize_escape_sequence(writer):
    logger.add(writer, format="{message}", colorize=False, sanitize=True)
    logger.info("\x1b[2J")
    assert writer.read() == "\\x1b[2J\n"


def test_sanitize_line_break(writer):
    logger.add(writer, format="{message}", colorize=False, sanitize=True)
    logger.info("forged\nfake | INFO | module:func:1 - injected")
    assert writer.read() == "forged\\x0afake | INFO | module:func:1 - injected\n"


def test_sanitize_all_control_characters(writer):
    logger.add(writer, format="{message}", colorize=False, sanitize=True)
    logger.info("a\x00b\x07c\x1bd\x7fe\x9bf")
    assert writer.read() == "a\\x00b\\x07c\\x1bd\\x7fe\\x9bf\n"


def test_sanitize_does_not_alter_format_nor_terminator(writer):
    logger.add(writer, format="{level} {message}", colorize=False, sanitize=True)
    logger.info("Test")
    assert writer.read() == "INFO Test\n"


def test_sanitize_with_formatting_arguments(writer):
    logger.add(writer, format="{message}", colorize=False, sanitize=True)
    logger.info("Hello {}", "\x1b[31mworld")
    assert writer.read() == "Hello \\x1b[31mworld\n"


def test_sanitize_with_raw(writer):
    logger.add(writer, format="{message}", colorize=False, sanitize=True)
    logger.opt(raw=True).info("\x1b[2J")
    assert writer.read() == "\\x1b[2J"


def test_sanitize_with_colorize(writer):
    logger.add(writer, format="<red>{message}</red>", colorize=True, sanitize=True)
    logger.info("\x1b[2J")
    assert writer.read() == "\x1b[31m\\x1b[2J\x1b[0m\n"
