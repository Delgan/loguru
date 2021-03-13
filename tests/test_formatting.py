import re

import pytest

from loguru import logger


@pytest.mark.parametrize(
    "format, validator",
    [
        ("{name}", lambda r: r == "tests.test_formatting"),
        ("{time}", lambda r: re.fullmatch(r"\d+-\d+-\d+T\d+:\d+:\d+[.,]\d+[+-]\d{4}", r)),
        ("{elapsed}", lambda r: re.fullmatch(r"\d:\d{2}:\d{2}\.\d{6}", r)),
        ("{elapsed.seconds}", lambda r: re.fullmatch(r"\d+", r)),
        ("{line}", lambda r: re.fullmatch(r"\d+", r)),
        ("{level}", lambda r: r == "DEBUG"),
        ("{level.name}", lambda r: r == "DEBUG"),
        ("{level.no}", lambda r: r == "10"),
        ("{level.icon}", lambda r: r == "🐞"),
        ("{file}", lambda r: r == "test_formatting.py"),
        ("{file.name}", lambda r: r == "test_formatting.py"),
        ("{file.path}", lambda r: r == __file__),
        ("{function}", lambda r: r == "test_log_formatters"),
        ("{module}", lambda r: r == "test_formatting"),
        ("{thread}", lambda r: re.fullmatch(r"\d+", r)),
        ("{thread.id}", lambda r: re.fullmatch(r"\d+", r)),
        ("{thread.name}", lambda r: isinstance(r, str) and r != ""),
        ("{process}", lambda r: re.fullmatch(r"\d+", r)),
        ("{process.id}", lambda r: re.fullmatch(r"\d+", r)),
        ("{process.name}", lambda r: isinstance(r, str) and r != ""),
        ("{message}", lambda r: r == "Message"),
        ("%s {{a}} 天 {{1}} %d", lambda r: r == "%s {a} 天 {1} %d"),
    ],
)
@pytest.mark.parametrize("use_log_function", [False, True])
def test_log_formatters(format, validator, writer, use_log_function):
    message = "Message"

    logger.add(writer, format=format)

    if use_log_function:
        logger.log("DEBUG", message)
    else:
        logger.debug(message)

    result = writer.read().rstrip("\n")
    assert validator(result)


@pytest.mark.parametrize(
    "format, validator",
    [
        ("{time}.log", lambda r: re.fullmatch(r"\d+-\d+-\d+_\d+-\d+-\d+\_\d+.log", r)),
        ("%s_{{a}}_天_{{1}}_%d", lambda r: r == "%s_{a}_天_{1}_%d"),
    ],
)
@pytest.mark.parametrize("part", ["file", "dir", "both"])
def test_file_formatters(tmpdir, format, validator, part):
    if part == "file":
        file = tmpdir.join(format)
    elif part == "dir":
        file = tmpdir.join(format, "log.log")
    elif part == "both":
        file = tmpdir.join(format, format)

    logger.add(str(file))
    logger.debug("Message")

    files = [f for f in tmpdir.visit() if f.check(file=1)]

    assert len(files) == 1

    file = files[0]

    if part == "file":
        assert validator(file.basename)
    elif part == "dir":
        assert file.basename == "log.log"
        assert validator(file.dirpath().basename)
    elif part == "both":
        assert validator(file.basename)
        assert validator(file.dirpath().basename)


@pytest.mark.parametrize(
    "message, args, kwargs, expected",
    [
        ("{1, 2, 3} - {0} - {", [], {}, "{1, 2, 3} - {0} - {"),
        ("{} + {} = {}", [1, 2, 3], {}, "1 + 2 = 3"),
        ("{a} + {b} = {c}", [], dict(a=1, b=2, c=3), "1 + 2 = 3"),
        ("{0} + {two} = {1}", [1, 3], dict(two=2, nope=4), "1 + 2 = 3"),
        (
            "{self} or {message} or {level}",
            [],
            dict(self="a", message="b", level="c"),
            "a or b or c",
        ),
        ("{:.2f}", [1], {}, "1.00"),
        ("{0:0{three}d}", [5], dict(three=3), "005"),
        ("{{nope}} {my_dict} {}", ["{{!}}"], dict(my_dict={"a": 1}), "{nope} {'a': 1} {{!}}"),
    ],
)
@pytest.mark.parametrize("use_log_function", [False, True])
def test_log_formatting(writer, message, args, kwargs, expected, use_log_function):
    logger.add(writer, format="{message}", colorize=False)

    if use_log_function:
        logger.log(10, message, *args, **kwargs)
    else:
        logger.debug(message, *args, **kwargs)

    assert writer.read() == expected + "\n"


def test_f_globals_name_absent(writer, f_globals_name_absent):
    logger.add(writer, format="{name} {message}", colorize=False)
    logger.info("Foobar")
    assert writer.read() == "None Foobar\n"


def test_extra_formatting(writer):
    logger.configure(extra={"test": "my_test", "dict": {"a": 10}})
    logger.add(writer, format="{extra[test]} -> {extra[dict]} -> {message}")
    logger.debug("level: {name}", name="DEBUG")
    assert writer.read() == "my_test -> {'a': 10} -> level: DEBUG\n"


def test_kwargs_in_extra_dict():
    extra_dicts = []
    messages = []

    def sink(message):
        extra_dicts.append(message.record["extra"])
        messages.append(str(message))

    logger.add(sink, format="{message}")
    logger.info("A")
    logger.info("B", foo=123)
    logger.bind(merge=True).info("C", other=False)
    logger.bind(override=False).info("D", override=True)
    logger.info("Formatted kwargs: {foobar}", foobar=123)
    logger.info("Ignored args: {}", 456)
    logger.info("Both: {foobar} {}", 456, foobar=123)
    logger.opt(lazy=True).info("Lazy: {lazy}", lazy=lambda: 789)

    assert messages == [
        "A\n",
        "B\n",
        "C\n",
        "D\n",
        "Formatted kwargs: 123\n",
        "Ignored args: 456\n",
        "Both: 123 456\n",
        "Lazy: 789\n",
    ]

    assert extra_dicts == [
        {},
        {"foo": 123},
        {"merge": True, "other": False},
        {"override": True},
        {"foobar": 123},
        {},
        {"foobar": 123},
        {"lazy": 789},
    ]


def test_non_string_message(writer):
    logger.add(writer, format="{message}")

    logger.info(1)
    logger.info({})
    logger.info(b"test")

    assert writer.read() == "1\n{}\nb'test'\n"


@pytest.mark.parametrize("colors", [True, False])
def test_non_string_message_is_str_in_record(writer, colors):
    output = ""

    def sink(message):
        nonlocal output
        assert isinstance(message.record["message"], str)
        output += message

    def format(record):
        assert isinstance(record["message"], str)
        return "[{message}]\n"

    logger.add(sink, format=format, catch=False)
    logger.opt(colors=colors).info(123)
    assert output == "[123]\n"


@pytest.mark.parametrize("colors", [True, False])
def test_missing_positional_field_during_formatting(writer, colors):
    logger.add(writer)

    with pytest.raises(IndexError):
        logger.opt(colors=colors).info("Foo {} {}", 123)


@pytest.mark.parametrize("colors", [True, False])
def test_missing_named_field_during_formatting(writer, colors):
    logger.add(writer)

    with pytest.raises(KeyError):
        logger.opt(colors=colors).info("Foo {bar}", baz=123)


def test_not_formattable_message(writer):
    logger.add(writer)

    with pytest.raises(AttributeError):
        logger.info(123, baz=456)


def test_not_formattable_message_with_colors(writer):
    logger.add(writer)

    with pytest.raises(TypeError):
        logger.opt(colors=True).info(123, baz=456)


def test_invalid_color_markup(writer):
    with pytest.raises(ValueError):
        logger.add(writer, format="<red>Not closed tag", colorize=True)
