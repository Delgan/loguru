import pytest

from loguru import logger


@pytest.mark.parametrize(
    ("message", "format", "expected"),
    [
        ("a", "Message: {message}", "Message: a\n"),
        ("b", "Nope", "Nope\n"),
        ("c", "{level} {message} {level}", "DEBUG c DEBUG\n"),
        ("d", "{message} {level} {level.no} {level.name}", "d DEBUG 10 DEBUG\n"),
        ("e", lambda _: "{message}", "e"),
        ("f", lambda r: "{message} " + r["level"].name, "f DEBUG"),
    ],
)
def test_format(message, format, expected, writer):
    logger.add(writer, format=format)
    logger.debug(message)
    assert writer.read() == expected


def test_progressive_format(writer):
    def formatter(record):
        fmt = "[{level.name}] {message}"
        if "noend" not in record["extra"]:
            fmt += "\n"
        return fmt

    logger.add(writer, format=formatter)
    logger.bind(noend=True).debug("Start: ")
    for _ in range(5):
        logger.opt(raw=True).debug(".")
    logger.opt(raw=True).debug("\n")
    logger.debug("End")
    assert writer.read() == ("[DEBUG] Start: .....\n" "[DEBUG] End\n")


def test_function_format_without_exception(writer):
    logger.add(writer, format=lambda _: "{message}\n")
    try:
        1 / 0  # noqa: B018
    except ZeroDivisionError:
        logger.exception("Error!")
    assert writer.read() == "Error!\n"


def test_function_format_with_exception(writer):
    logger.add(writer, format=lambda _: "{message}\n{exception}")
    try:
        1 / 0  # noqa: B018
    except ZeroDivisionError:
        logger.exception("Error!")
    lines = writer.read().splitlines()
    assert lines[0] == "Error!"
    assert lines[-1] == "ZeroDivisionError: division by zero"


@pytest.mark.parametrize("format", [-1, 3.4, object()])
def test_invalid_format(writer, format):
    with pytest.raises(TypeError):
        logger.add(writer, format=format)


@pytest.mark.parametrize("format", ["<red>", "</red>", "</level><level>", "</>", "<foobar>"])
def test_invalid_markups(writer, format):
    with pytest.raises(
        ValueError, match=r"^Invalid format, color markups could not be parsed correctly$"
    ):
        logger.add(writer, format=format)


@pytest.mark.parametrize("colorize", [True, False])
def test_markup_in_field(writer, colorize):
    class F:
        def __format__(self, spec):
            return spec

    logger.add(writer, format="{extra[f]:</>} {extra[f]: <blue> } {message}", colorize=colorize)
    logger.bind(f=F()).info("Test")

    assert writer.read() == "</>  <blue>  Test\n"


def test_invalid_format_builtin(writer):
    with pytest.raises(ValueError, match=r".* most likely a mistake"):
        logger.add(writer, format=format)


# ── Tests for invalid format key validation (issue #1450) ─────────────────────

@pytest.mark.parametrize(
    "fmt",
    [
        "{time} {INVALID_KEY} {message}",
        "{nonexistent}",
        "{time} {BAD1} {BAD2} {message}",
        "{UPPER_CASE}",
    ],
)
def test_invalid_format_key_raises_at_add_time(writer, fmt):
    """logger.add() must raise ValueError immediately for unknown format keys.

    Previously, the error was a cryptic KeyError raised on every log() call,
    causing the message to be silently dropped. Now the user gets a clear
    ValueError at configuration time.
    """
    with pytest.raises(ValueError, match=r"Invalid format key\(s\)"):
        logger.add(writer, format=fmt)


@pytest.mark.parametrize(
    "fmt",
    [
        "{time} {level} {message}",
        "{time} {level.name} {message}",
        "{time} {level.no} {message}",
        "{extra[mykey]} {message}",
        "{file.name} {line} {function} {message}",
        "{process.id} {thread.name} {message}",
        "{elapsed} {module} {name} {message}",
    ],
)
def test_valid_format_keys_accepted(writer, fmt):
    """All built-in record keys and their attributes must be accepted."""
    logger.add(writer, format=fmt)   # must not raise


def test_invalid_format_key_error_lists_allowed_keys(writer):
    """The ValueError message must list both the bad key and all allowed keys."""
    with pytest.raises(ValueError, match=r"'BADKEY'") as exc_info:
        logger.add(writer, format="{time} {BADKEY} {message}")
    msg = str(exc_info.value)
    # All valid keys must appear in the error
    for key in ("elapsed", "exception", "extra", "file", "function", "level",
                "line", "message", "module", "name", "process", "thread", "time"):
        assert key in msg, f"Expected key {key!r} in error message, got: {msg}"


def test_multiple_invalid_keys_listed(writer):
    """All invalid keys (not just the first) must appear in the ValueError."""
    with pytest.raises(ValueError, match=r"Invalid format key\(s\)") as exc_info:
        logger.add(writer, format="{FOO} {BAR} {message}")
    msg = str(exc_info.value)
    assert "'BAR'" in msg and "'FOO'" in msg
