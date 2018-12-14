import re
import pytest
from loguru import logger
from ansimarkup import AnsiMarkupError


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
        ("{file.path}", lambda r: re.fullmatch(r".*tests[/\\]test_formatting.py", r)),
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

    logger.add(file.realpath())
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


def test_extra_formatting(writer):
    logger.configure(extra={"test": "my_test", "dict": {"a": 10}})
    logger.add(writer, format="{extra[test]} -> {extra[dict]} -> {message}")
    logger.debug("level: {name}", name="DEBUG")
    assert writer.read() == "my_test -> {'a': 10} -> level: DEBUG\n"


def test_invalid_color_markup(writer):
    with pytest.raises(AnsiMarkupError):
        logger.add(writer, format="<red>Not closed tag", colorize=True)
