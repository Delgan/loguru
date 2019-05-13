import pytest
import sys
from loguru import logger
from loguru._ansimarkup import AnsiMarkup


def parse(text, colorize=True):
    if colorize:
        return AnsiMarkup(strip=False).feed(text, strict=True)
    else:
        return AnsiMarkup(strip=True).feed(text, strict=True)


def test_record(writer):
    logger.add(writer, format="{message}")

    logger.opt(record=True).debug("1")
    logger.opt(record=True).debug("2 {record[level]}")
    logger.opt(record=True).log(11, "3 {0} {a} {record[level].no}", 4, a=5)

    assert writer.read() == "1\n2 DEBUG\n3 4 5 11\n"


def test_exception_boolean(writer):
    logger.add(writer, format="{level.name}: {message}")

    try:
        1 / 0
    except:
        logger.opt(exception=True).debug("Error {0} {record}", 1, record="test")

    lines = writer.read().strip().splitlines()

    assert lines[0] == "DEBUG: Error 1 test"
    assert lines[-1] == "ZeroDivisionError: division by zero"


def test_exception_exc_info(writer):
    logger.add(writer, format="{message}")

    try:
        1 / 0
    except:
        exc_info = sys.exc_info()

    logger.opt(exception=exc_info).debug("test")

    lines = writer.read().strip().splitlines()

    assert lines[0] == "test"
    assert lines[-1] == "ZeroDivisionError: division by zero"


def test_exception_class(writer):
    logger.add(writer, format="{message}")

    try:
        1 / 0
    except:
        _, exc_class, _ = sys.exc_info()

    logger.opt(exception=exc_class).debug("test")

    lines = writer.read().strip().splitlines()

    assert lines[0] == "test"
    assert lines[-1] == "ZeroDivisionError: division by zero"


def test_exception_log_funcion(writer):
    logger.add(writer, format="{level.no} {message}")

    try:
        1 / 0
    except:
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

    a = logger.add(writer, level=15, format="{level.no} => {message}")
    b = logger.add(writer, level=20, format="{level.no} => {message}")

    logger.log(17, "4: {}", counter)
    logger.opt(lazy=True).log(14, "5: {lazy}", lazy=lambda: counter)

    logger.remove(a)

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


def test_ansi(writer):
    logger.add(writer, format="<red>a</red> {message}", colorize=True)
    logger.opt(ansi=True).debug("<blue>b</blue>")
    logger.opt(ansi=True).log(20, "<y>c</y>")

    assert writer.read() == parse("<red>a</red> <blue>b</blue>\n" "<red>a</red> <y>c</y>\n")


def test_ansi_not_colorize(writer):
    logger.add(writer, format="<red>a</red> {message}", colorize=False)
    logger.opt(ansi=True).debug("<blue>b</blue>")
    assert writer.read() == parse("<red>a</red> <blue>b</blue>\n", colorize=False)


def test_ansi_dont_color_unrelated(writer):
    logger.add(writer, format="{message} {extra[trap]}", colorize=True)
    logger.bind(trap="<red>B</red>").opt(ansi=True).debug("<red>A</red>")
    assert writer.read() == parse("<red>A</red>") + " <red>B</red>\n"


def test_ansi_dont_strip_unrelated(writer):
    logger.add(writer, format="{message} {extra[trap]}", colorize=False)
    logger.bind(trap="<red>B</red>").opt(ansi=True).debug("<red>A</red>")
    assert writer.read() == parse("<red>A</red>", colorize=False) + " <red>B</red>\n"


def test_ansi_dont_raise_unrelated_colorize(writer):
    logger.add(writer, format="{message} {extra[trap]}", colorize=True, catch=False)
    logger.bind(trap="</red>").opt(ansi=True).debug("A")
    assert writer.read() == "A </red>\n"


def test_ansi_dont_raise_unrelated_not_colorize(writer):
    logger.add(writer, format="{message} {extra[trap]}", colorize=False, catch=False)
    logger.bind(trap="</red>").opt(ansi=True).debug("A")
    assert writer.read() == "A </red>\n"


def test_ansi_dont_raise_unrelated_colorize_dynamic(writer):
    logger.add(writer, format=lambda x: "{message} {extra[trap]}", colorize=True, catch=False)
    logger.bind(trap="</red>").opt(ansi=True).debug("A")
    assert writer.read() == "A </red>"


def test_ansi_dont_raise_unrelated_not_colorize_dynamic(writer):
    logger.add(writer, format=lambda x: "{message} {extra[trap]}", colorize=False, catch=False)
    logger.bind(trap="</red>").opt(ansi=True).debug("A")
    assert writer.read() == "A </red>"


@pytest.mark.parametrize("colorize", [True, False])
def test_ansi_with_record(writer, colorize):
    logger.add(writer, format="{message}", colorize=colorize)
    logger_ = logger.bind(start="<red>", end="</red>")
    logger_.opt(ansi=True, record=True).debug("{record[extra][start]}B{record[extra][end]}")
    assert writer.read() == parse("<red>B</red>\n", colorize=colorize)


@pytest.mark.parametrize("colorize", [True, False])
def test_ansi_nested(writer, colorize):
    logger.add(writer, format="(<red>[{message}]</red>)", colorize=colorize)
    logger.opt(ansi=True).debug("A<green>B</green>C<blue>D</blue>E")
    assert writer.read() == parse(
        "(<red>[A<green>B</green>C<blue>D</blue>E]</red>)\n", colorize=colorize
    )


@pytest.mark.parametrize("colorize", [True, False])
def test_ansi_message_in_record(colorize):
    message = None

    def sink(msg):
        nonlocal message
        message = msg.record["message"]

    logger.add(sink, colorize=colorize)
    logger.opt(ansi=True).debug("<red>Test</red>")
    assert message == "<red>Test</red>"


@pytest.mark.parametrize("message", ["<red>", "</red>", "X </red> <red> Y"])
@pytest.mark.parametrize("colorize", [True, False])
def test_invalid_markup_in_message(writer, message, colorize):
    logger.add(writer, format="<red>{message}</red>", colorize=colorize, catch=False)
    with pytest.raises(ValueError):
        logger.opt(ansi=True).debug(message)


@pytest.mark.parametrize("colorize", [True, False])
def test_ansi_with_args(writer, colorize):
    logger.add(writer, format="=> {message} <=", colorize=colorize)
    logger.opt(ansi=True).debug("the {0}test{end}", "<red>", end="</red>")
    assert writer.read() == parse("=> the <red>test</red> <=\n", colorize=colorize)


@pytest.mark.parametrize("colorize", [True, False])
def test_ansi_with_level(writer, colorize):
    logger.add(writer, format="{message}", colorize=colorize)
    logger.level("DEBUG", color="<green>")
    logger.opt(ansi=True).debug("a <level>level</level> b")
    assert writer.read() == parse("a <green>level</green> b\n", colorize=colorize)


@pytest.mark.parametrize("colorize", [True, False])
def test_ansi_double_message(writer, colorize):
    logger.add(
        writer, format="<red><b>{message}...</b> - <c>...{message}</c></red>", colorize=colorize
    )
    logger.opt(ansi=True).debug("<g>foo</g> bar <g>baz</g>")

    assert writer.read() == parse(
        "<red><b><g>foo</g> bar <g>baz</g>...</b> - <c>...<g>foo</g> bar <g>baz</g></c></red>\n",
        colorize=colorize,
    )


@pytest.mark.parametrize("colorize", [True, False])
def test_ansi_multiple_calls(writer, colorize):
    logger.add(writer, format="{message}", colorize=colorize)
    logger.opt(ansi=True).debug("a <red>foo</red> b")
    logger.opt(ansi=True).debug("a <red>foo</red> b")
    assert writer.read() == parse("a <red>foo</red> b\na <red>foo</red> b\n", colorize=colorize)


@pytest.mark.parametrize("colorize", [True, False])
def test_ansi_multiple_calls_level_color_changed(writer, colorize):
    logger.add(writer, format="{message}", colorize=colorize)
    logger.level("INFO", color="<blue>")
    logger.opt(ansi=True).info("a <level>foo</level> b")
    logger.level("INFO", color="<red>")
    logger.opt(ansi=True).info("a <level>foo</level> b")
    assert writer.read() == parse("a <blue>foo</blue> b\na <red>foo</red> b\n", colorize=colorize)


@pytest.mark.parametrize("colorize", [True, False])
def test_ansi_with_dynamic_formatter(writer, colorize):
    logger.add(writer, format=lambda r: "<red>{message}</red>", colorize=colorize)
    logger.opt(ansi=True).debug("<b>a</b> <y>b</y>")
    assert writer.read() == parse("<red><b>a</b> <y>b</y></red>", colorize=colorize)


@pytest.mark.parametrize("colorize", [True, False])
def test_ansi_with_format_specs(writer, colorize):
    fmt = "<g>{level.no:03d} {message!s:} {{nope}} {extra[a][b]!r}</g>"
    logger.add(writer, colorize=colorize, format=fmt)
    logger.bind(a={"b": "c"}).opt(ansi=True).debug("<g>{X}</g>")
    assert writer.read() == parse("<g>010 <g>{X}</g> {nope} 'c'</g>\n", colorize=colorize)


@pytest.mark.parametrize("colorize", [True, False])
def test_ansi_with_message_specs(writer, colorize):
    logger.add(writer, colorize=colorize, format="<g>{message}</g>")
    logger.opt(ansi=True).debug("{} <b>A</b> {{nope}} {key:03d} {let!r}", 1, key=10, let="c")
    logger.opt(ansi=True).debug("<b>{0:0{1}d}</b>", 2, 4)
    assert writer.read() == parse(
        "<g>1 <b>A</b> {nope} 010 'c'</g>\n<g><b>0002</b></g>\n", colorize=colorize
    )


@pytest.mark.parametrize("colorize", [True, False])
def test_ansi_message_used_as_spec(writer, colorize):
    logger.add(writer, colorize=colorize, format="{level.no:{message}} <red>{message}</red>")
    logger.opt(ansi=True).log(30, "03d")
    assert writer.read() == parse("030 <red>03d</red>\n", colorize=colorize)


@pytest.mark.parametrize("colorize", [True, False])
def test_ansi_message_getitem(writer, colorize):
    logger.add(writer, colorize=colorize, format="<red>{message[0]}</red>")
    logger.opt(ansi=True).info("ABC")
    assert writer.read() == parse("<red>A</red>\n", colorize=colorize)


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
def test_raw_with_ansi(writer, colorize):
    logger.add(writer, format="XYZ", colorize=colorize)
    logger.opt(raw=True, ansi=True).info("Raw <red>colors</red> and <lvl>level</lvl>")
    assert writer.read() == parse("Raw <red>colors</red> and <b>level</b>", colorize=colorize)


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
