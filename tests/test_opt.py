import sys
from unittest.mock import MagicMock

import pytest

from loguru import logger

from .conftest import parse


def test_record(writer):
    logger.add(writer, format="{message}")

    logger.opt(record=True).debug("1")
    logger.opt(record=True).debug("2 {record[level]}")
    logger.opt(record=True).log(11, "3 {0} {a} {record[level].no}", 4, a=5)

    assert writer.read() == "1\n2 DEBUG\n3 4 5 11\n"


def test_record_in_kwargs_too(writer):
    logger.add(writer, catch=False)

    with pytest.raises(TypeError, match=r"The message can't be formatted"):
        logger.opt(record=True).info("Foo {record}", record=123)


def test_record_not_in_extra():
    extra = None

    def sink(message):
        nonlocal extra
        extra = message.record["extra"]

    logger.add(sink, catch=False)

    logger.opt(record=True).info("Test")

    assert extra == {}


def test_kwargs_in_extra_of_record():
    message = None

    def sink(message_):
        nonlocal message
        message = message_

    logger.add(sink, format="{message}", catch=False)

    logger.opt(record=True).info("Test {record[extra][foo]}", foo=123)

    assert message == "Test 123\n"
    assert message.record["extra"] == {"foo": 123}


def test_exception_boolean(writer):
    logger.add(writer, format="{level.name}: {message}")

    try:
        1 / 0
    except Exception:
        logger.opt(exception=True).debug("Error {0} {record}", 1, record="test")

    lines = writer.read().strip().splitlines()

    assert lines[0] == "DEBUG: Error 1 test"
    assert lines[-1] == "ZeroDivisionError: division by zero"


def test_exception_exc_info(writer):
    logger.add(writer, format="{message}")

    try:
        1 / 0
    except Exception:
        exc_info = sys.exc_info()

    logger.opt(exception=exc_info).debug("test")

    lines = writer.read().strip().splitlines()

    assert lines[0] == "test"
    assert lines[-1] == "ZeroDivisionError: division by zero"


def test_exception_class(writer):
    logger.add(writer, format="{message}")

    try:
        1 / 0
    except Exception:
        _, exc_class, _ = sys.exc_info()

    logger.opt(exception=exc_class).debug("test")

    lines = writer.read().strip().splitlines()

    assert lines[0] == "test"
    assert lines[-1] == "ZeroDivisionError: division by zero"


def test_exception_log_funcion(writer):
    logger.add(writer, format="{level.no} {message}")

    try:
        1 / 0
    except Exception:
        logger.opt(exception=True).log(50, "Error")

    lines = writer.read().strip().splitlines()

    assert lines[0] == "50 Error"
    assert lines[-1] == "ZeroDivisionError: division by zero"


def test_lazy(writer):
    counter = 0

    def laziness():
        nonlocal counter
        counter += 1
        return counter

    logger.add(writer, level=10, format="{level.no} => {message}")

    logger.opt(lazy=True).log(10, "1: {lazy}", lazy=laziness)
    logger.opt(lazy=True).log(5, "2: {0}", laziness)

    logger.remove()

    logger.opt(lazy=True).log(20, "3: {}", laziness)

    i = logger.add(writer, level=15, format="{level.no} => {message}")
    logger.add(writer, level=20, format="{level.no} => {message}")

    logger.log(17, "4: {}", counter)
    logger.opt(lazy=True).log(14, "5: {lazy}", lazy=lambda: counter)

    logger.remove(i)

    logger.opt(lazy=True).log(16, "6: {0}", lambda: counter)

    logger.opt(lazy=True).info("7: {}", laziness)
    logger.debug("7: {}", counter)

    assert writer.read() == "10 => 1: 1\n17 => 4: 1\n20 => 7: 2\n"


def test_logging_within_lazy_function(writer):
    logger.add(writer, level=20, format="{message}")

    def laziness():
        logger.trace("Nope")
        logger.warning("Yes Warn")

    logger.opt(lazy=True).trace("No", laziness)

    assert writer.read() == ""

    logger.opt(lazy=True).info("Yes", laziness)

    assert writer.read() == "Yes Warn\nYes\n"


def test_depth(writer):
    logger.add(writer, format="{function} : {message}")

    def a():
        logger.opt(depth=1).debug("Test 1")
        logger.opt(depth=0).debug("Test 2")
        logger.opt(depth=1).log(10, "Test 3")

    a()

    logger.remove()

    assert writer.read() == "test_depth : Test 1\na : Test 2\ntest_depth : Test 3\n"


def test_capture(writer):
    logger.add(writer, format="{message} {extra}")
    logger.opt(capture=False).info("No {}", 123, no=False)
    logger.opt(capture=False).info("Formatted: {fmt}", fmt=456)
    logger.opt(capture=False).info("Formatted bis: {} {fmt}", 123, fmt=456)
    assert writer.read() == "No 123 {}\nFormatted: 456 {}\nFormatted bis: 123 456 {}\n"


def test_colors(writer):
    logger.add(writer, format="<red>a</red> {message}", colorize=True)
    logger.opt(colors=True).debug("<blue>b</blue>")
    logger.opt(colors=True).log(20, "<y>c</y>")

    assert writer.read() == parse(
        "<red>a</red> <blue>b</blue>\n" "<red>a</red> <y>c</y>\n", strip=False
    )


def test_colors_not_colorize(writer):
    logger.add(writer, format="<red>a</red> {message}", colorize=False)
    logger.opt(colors=True).debug("<blue>b</blue>")
    assert writer.read() == parse("<red>a</red> <blue>b</blue>\n", strip=True)


def test_colors_doesnt_color_unrelated(writer):
    logger.add(writer, format="{message} {extra[trap]}", colorize=True)
    logger.bind(trap="<red>B</red>").opt(colors=True).debug("<red>A</red>")
    assert writer.read() == parse("<red>A</red>", strip=False) + " <red>B</red>\n"


def test_colors_doesnt_strip_unrelated(writer):
    logger.add(writer, format="{message} {extra[trap]}", colorize=False)
    logger.bind(trap="<red>B</red>").opt(colors=True).debug("<red>A</red>")
    assert writer.read() == parse("<red>A</red>", strip=True) + " <red>B</red>\n"


def test_colors_doesnt_raise_unrelated_colorize(writer):
    logger.add(writer, format="{message} {extra[trap]}", colorize=True, catch=False)
    logger.bind(trap="</red>").opt(colors=True).debug("A")
    assert writer.read() == "A </red>\n"


def test_colors_doesnt_raise_unrelated_not_colorize(writer):
    logger.add(writer, format="{message} {extra[trap]}", colorize=False, catch=False)
    logger.bind(trap="</red>").opt(colors=True).debug("A")
    assert writer.read() == "A </red>\n"


def test_colors_doesnt_raise_unrelated_colorize_dynamic(writer):
    logger.add(writer, format=lambda x: "{message} {extra[trap]}", colorize=True, catch=False)
    logger.bind(trap="</red>").opt(colors=True).debug("A")
    assert writer.read() == "A </red>"


def test_colors_doesnt_raise_unrelated_not_colorize_dynamic(writer):
    logger.add(writer, format=lambda x: "{message} {extra[trap]}", colorize=False, catch=False)
    logger.bind(trap="</red>").opt(colors=True).debug("A")
    assert writer.read() == "A </red>"


@pytest.mark.parametrize("colorize", [True, False])
def test_colors_within_record(writer, colorize):
    logger.add(writer, format="{message}", colorize=colorize)
    logger_ = logger.bind(start="<red>", end="</red>")
    logger_.opt(colors=True, record=True).debug("{record[extra][start]}B{record[extra][end]}")
    assert writer.read() == "<red>B</red>\n"


@pytest.mark.parametrize("colorize", [True, False])
def test_colors_nested(writer, colorize):
    logger.add(writer, format="(<red>[{message}]</red>)", colorize=colorize)
    logger.opt(colors=True).debug("A<green>B</green>C<blue>D</blue>E")
    assert writer.read() == parse(
        "(<red>[A<green>B</green>C<blue>D</blue>E]</red>)\n", strip=not colorize
    )


@pytest.mark.parametrize("colorize", [True, False])
def test_colors_stripped_in_message_record(colorize):
    message = None

    def sink(msg):
        nonlocal message
        message = msg.record["message"]

    logger.add(sink, colorize=colorize)
    logger.opt(colors=True).debug("<red>Test</red>")
    assert message == "Test"


@pytest.mark.parametrize("message", ["<red>", "</red>", "X </red> <red> Y"])
@pytest.mark.parametrize("colorize", [True, False])
def test_invalid_markup_in_message(writer, message, colorize):
    logger.add(writer, format="<red>{message}</red>", colorize=colorize, catch=False)
    with pytest.raises(ValueError):
        logger.opt(colors=True).debug(message)


@pytest.mark.parametrize("colorize", [True, False])
def test_colors_with_args(writer, colorize):
    logger.add(writer, format="=> {message} <=", colorize=colorize)
    logger.opt(colors=True).debug("the {0}test{end}", "<red>", end="</red>")
    assert writer.read() == "=> the <red>test</red> <=\n"


@pytest.mark.parametrize("colorize", [True, False])
def test_colors_with_level(writer, colorize):
    logger.add(writer, format="{message}", colorize=colorize)
    logger.level("DEBUG", color="<green>")
    logger.opt(colors=True).debug("a <level>level</level> b")
    assert writer.read() == parse("a <green>level</green> b\n", strip=not colorize)


@pytest.mark.parametrize("colorize", [True, False])
def test_colors_double_message(writer, colorize):
    logger.add(
        writer, format="<red><b>{message}...</b> - <c>...{message}</c></red>", colorize=colorize
    )
    logger.opt(colors=True).debug("<g>foo</g> bar <g>baz</g>")

    assert writer.read() == parse(
        "<red><b><g>foo</g> bar <g>baz</g>...</b> - <c>...<g>foo</g> bar <g>baz</g></c></red>\n",
        strip=not colorize,
    )


@pytest.mark.parametrize("colorize", [True, False])
def test_colors_multiple_calls(writer, colorize):
    logger.add(writer, format="{message}", colorize=colorize)
    logger.opt(colors=True).debug("a <red>foo</red> b")
    logger.opt(colors=True).debug("a <red>foo</red> b")
    assert writer.read() == parse("a <red>foo</red> b\na <red>foo</red> b\n", strip=not colorize)


@pytest.mark.parametrize("colorize", [True, False])
def test_colors_multiple_calls_level_color_changed(writer, colorize):
    logger.add(writer, format="{message}", colorize=colorize)
    logger.level("INFO", color="<blue>")
    logger.opt(colors=True).info("a <level>foo</level> b")
    logger.level("INFO", color="<red>")
    logger.opt(colors=True).info("a <level>foo</level> b")
    assert writer.read() == parse("a <blue>foo</blue> b\na <red>foo</red> b\n", strip=not colorize)


@pytest.mark.parametrize("colorize", [True, False])
def test_colors_with_dynamic_formatter(writer, colorize):
    logger.add(writer, format=lambda r: "<red>{message}</red>", colorize=colorize)
    logger.opt(colors=True).debug("<b>a</b> <y>b</y>")
    assert writer.read() == parse("<red><b>a</b> <y>b</y></red>", strip=not colorize)


@pytest.mark.parametrize("colorize", [True, False])
def test_colors_with_format_specs(writer, colorize):
    fmt = "<g>{level.no:03d} {message:} {message!s:} {{nope}} {extra[a][b]!r}</g>"
    logger.add(writer, colorize=colorize, format=fmt)
    logger.bind(a={"b": "c"}).opt(colors=True).debug("<g>{X}</g>")
    assert writer.read() == parse("<g>010 <g>{X}</g> {X} {nope} 'c'</g>\n", strip=not colorize)


@pytest.mark.parametrize("colorize", [True, False])
def test_colors_with_message_specs(writer, colorize):
    logger.add(writer, colorize=colorize, format="<g>{message}</g>")
    logger.opt(colors=True).debug("{} <b>A</b> {{nope}} {key:03d} {let!r}", 1, key=10, let="c")
    logger.opt(colors=True).debug("<b>{0:0{1}d}</b>", 2, 4)
    assert writer.read() == parse(
        "<g>1 <b>A</b> {nope} 010 'c'</g>\n<g><b>0002</b></g>\n", strip=not colorize
    )


@pytest.mark.parametrize("colorize", [True, False])
def test_colored_string_used_as_spec(writer, colorize):
    logger.add(writer, colorize=colorize, format="{level.no:{message}} <red>{message}</red>")
    logger.opt(colors=True).log(30, "03d")
    assert writer.read() == parse("030 <red>03d</red>\n", strip=not colorize)


@pytest.mark.parametrize("colorize", [True, False])
def test_colored_string_getitem(writer, colorize):
    logger.add(writer, colorize=colorize, format="<red>{message[0]}</red>")
    logger.opt(colors=True).info("ABC")
    assert writer.read() == parse("<red>A</red>\n", strip=not colorize)


@pytest.mark.parametrize("colorize", [True, False])
def test_colors_without_formatting_args(writer, colorize):
    string = "{} This { should } not } raise {"
    logger.add(writer, colorize=colorize, format="{message}")
    logger.opt(colors=True).info(string)
    assert writer.read() == string + "\n"


@pytest.mark.parametrize("colorize", [True, False])
def test_colors_with_recursion_depth_exceeded_in_format(writer, colorize):
    with pytest.raises(ValueError, match=r"Invalid format"):
        logger.add(writer, format="{message:{message:{message:}}}", colorize=colorize)


@pytest.mark.parametrize("colorize", [True, False])
def test_colors_with_recursion_depth_exceeded_in_message(writer, colorize):
    logger.add(writer, format="{message}", colorize=colorize)

    with pytest.raises(ValueError, match=r"Max string recursion exceeded"):
        logger.opt(colors=True).info("{foo:{foo:{foo:}}}", foo=123)


@pytest.mark.parametrize("colorize", [True, False])
def test_colors_with_auto_indexing(writer, colorize):
    logger.add(writer, format="{message}", colorize=colorize)
    logger.opt(colors=True).info("<red>{}</red> <green>{}</green>", "foo", "bar")
    assert writer.read() == parse("<red>foo</red> <green>bar</green>\n", strip=not colorize)


@pytest.mark.parametrize("colorize", [True, False])
def test_colors_with_manual_indexing(writer, colorize):
    logger.add(writer, format="{message}", colorize=colorize)
    logger.opt(colors=True).info("<red>{1}</red> <green>{0}</green>", "foo", "bar")
    assert writer.read() == parse("<red>bar</red> <green>foo</green>\n", strip=not colorize)


@pytest.mark.parametrize("colorize", [True, False])
@pytest.mark.parametrize("message", ["{} {0}", "{1} {}"])
def test_colors_with_invalid_indexing(writer, colorize, message):
    logger.add(writer, format="{message}", colorize=colorize)

    with pytest.raises(ValueError, match=r"cannot switch"):
        logger.opt(colors=True).debug(message, 1, 2, 3)


def test_raw(writer):
    logger.add(writer, format="", colorize=True)
    logger.opt(raw=True).info("Raw {}", "message")
    logger.opt(raw=True).log(30, " + The end")
    assert writer.read() == "Raw message + The end"


def test_raw_with_format_function(writer):
    logger.add(writer, format=lambda _: "{time} \n")
    logger.opt(raw=True).debug("Raw {message} bis", message="message")
    assert writer.read() == "Raw message bis"


@pytest.mark.parametrize("colorize", [True, False])
def test_raw_with_colors(writer, colorize):
    logger.add(writer, format="XYZ", colorize=colorize)
    logger.opt(raw=True, colors=True).info("Raw <red>colors</red> and <lvl>level</lvl>")
    assert writer.read() == parse("Raw <red>colors</red> and <b>level</b>", strip=not colorize)


def test_args_with_colors_not_formatted_twice(capsys):
    logger.add(sys.stdout, format="{message}", colorize=True)
    logger.add(sys.stderr, format="{message}", colorize=False)
    a = MagicMock(__format__=MagicMock(return_value="a"))
    b = MagicMock(__format__=MagicMock(return_value="b"))

    logger.opt(colors=True).info("{} <red>{foo}</red>", a, foo=b)
    out, err = capsys.readouterr()
    assert out == parse("a <red>b</red>\n")
    assert err == "a b\n"
    assert a.__format__.call_count == 1
    assert b.__format__.call_count == 1


@pytest.mark.parametrize("colorize", [True, False])
def test_level_tag_wrapping_with_colors(writer, colorize):
    logger.add(writer, format="<level>FOO {message} BAR</level>", colorize=colorize)
    logger.opt(colors=True).info("> foo <red>{}</> bar <lvl>{}</> baz <green>{}</green> <", 1, 2, 3)
    logger.opt(colors=True).log(33, "<lvl> {} <red>{}</red> {} </lvl>", 1, 2, 3)

    assert writer.read() == parse(
        "<b>FOO > foo <red>1</red> bar <b>2</b> baz <green>3</green> < BAR</b>\n"
        "<level>FOO <level> 1 <red>2</red> 3 </level> BAR</level>\n",
        strip=not colorize,
    )


@pytest.mark.parametrize("dynamic_format", [True, False])
@pytest.mark.parametrize("colorize", [True, False])
@pytest.mark.parametrize("colors", [True, False])
@pytest.mark.parametrize("raw", [True, False])
@pytest.mark.parametrize("use_log", [True, False])
@pytest.mark.parametrize("use_arg", [True, False])
def test_all_colors_combinations(writer, dynamic_format, colorize, colors, raw, use_log, use_arg):
    format_ = "<level>{level.no:03}</level> <red>{message}</red>"
    message = "<green>The</green> <lvl>{}</lvl>"
    arg = "message"

    def formatter(_):
        return format_ + "\n"

    logger.add(writer, format=formatter if dynamic_format else format_, colorize=colorize)

    logger_ = logger.opt(colors=colors, raw=raw)

    if use_log:
        if use_arg:
            logger_.log(20, message, arg)
        else:
            logger_.log(20, message.format(arg))
    else:
        if use_arg:
            logger_.info(message, arg)
        else:
            logger_.info(message.format(arg))

    if use_log:
        if raw:
            if colors:
                expected = parse("<green>The</green> <level>message</level>", strip=not colorize)
            else:
                expected = "<green>The</green> <lvl>message</lvl>"
        else:
            if colors:
                expected = parse(
                    "<level>020</level> <red><green>The</green> <level>message</level></red>\n",
                    strip=not colorize,
                )
            else:
                expected = (
                    parse("<level>020</level> <red>%s</red>\n", strip=not colorize)
                    % "<green>The</green> <lvl>message</lvl>"
                )

    else:
        if raw:
            if colors:
                expected = parse("<green>The</green> <b>message</b>", strip=not colorize)
            else:
                expected = "<green>The</green> <lvl>message</lvl>"
        else:
            if colors:
                expected = parse(
                    "<b>020</b> <red><green>The</green> <b>message</b></red>\n", strip=not colorize
                )
            else:
                expected = (
                    parse("<b>020</b> <red>%s</red>\n", strip=not colorize)
                    % "<green>The</green> <lvl>message</lvl>"
                )

    assert writer.read() == expected


def test_raw_with_record(writer):
    logger.add(writer, format="Nope\n")
    logger.opt(raw=True, record=True).debug("Raw in '{record[function]}'\n")
    assert writer.read() == "Raw in 'test_raw_with_record'\n"


def test_keep_extra(writer):
    logger.configure(extra=dict(test=123))
    logger.add(writer, format="{extra[test]}")
    logger.opt().debug("")
    logger.opt().log(50, "")

    assert writer.read() == "123\n123\n"


def test_before_bind(writer):
    logger.add(writer, format="{message}")
    logger.opt(record=True).bind(key="value").info("{record[level]}")
    assert writer.read() == "INFO\n"


def test_deprecated_ansi_argument(writer):
    logger.add(writer, format="{message}", colorize=True)
    with pytest.warns(DeprecationWarning):
        logger.opt(ansi=True).info("Foo <red>bar</red> baz")
    assert writer.read() == parse("Foo <red>bar</red> baz\n")


@pytest.mark.parametrize("colors", [True, False])
def test_message_update_not_overridden_by_patch(writer, colors):
    def patcher(record):
        record["message"] += " [Patched]"

    logger.add(writer, format="{level} {message}", colorize=True)
    logger.patch(patcher).opt(colors=colors).info("Message")

    assert writer.read() == "INFO Message [Patched]\n"


@pytest.mark.parametrize("colors", [True, False])
def test_message_update_not_overridden_by_format(writer, colors):
    def formatter(record):
        record["message"] += " [Formatted]"
        return "{level} {message}\n"

    logger.add(writer, format=formatter, colorize=True)
    logger.opt(colors=colors).info("Message")

    assert writer.read() == "INFO Message [Formatted]\n"


@pytest.mark.parametrize("colors", [True, False])
def test_message_update_not_overridden_by_filter(writer, colors):
    def filter(record):
        record["message"] += " [Filtered]"
        return True

    logger.add(writer, format="{level} {message}", filter=filter, colorize=True)
    logger.opt(colors=colors).info("Message")

    assert writer.read() == "INFO Message [Filtered]\n"


@pytest.mark.parametrize("colors", [True, False])
def test_message_update_not_overridden_by_raw(writer, colors):
    logger.add(writer, colorize=True)
    logger.patch(lambda r: r.update(message="Updated!")).opt(raw=True, colors=colors).info("Raw!")
    assert writer.read() == "Updated!"


def test_overridden_message_ignore_colors(writer):
    def formatter(record):
        record["message"] += " <blue>[Ignored]</blue> </xyz>"
        return "{message}\n"

    logger.add(writer, format=formatter, colorize=True)
    logger.opt(colors=True).info("<red>Message</red>")

    assert writer.read() == "Message <blue>[Ignored]</blue> </xyz>\n"
