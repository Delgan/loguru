import pytest
import sys
from loguru import logger
import ansimarkup


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
    assert writer.read() == ansimarkup.parse(
        "<red>a</red> <blue>b</blue>\n" "<red>a</red> <y>c</y>\n"
    )


def test_ansi_not_colorize(writer):
    logger.add(writer, format="<red>a</red> {message}", colorize=False)
    logger.opt(ansi=True).debug("<blue>b</blue>")
    assert writer.read() == ansimarkup.strip("<red>a</red> <blue>b</blue>\n")


def test_ansi_dont_color_unrelated(writer):
    logger.add(writer, format="{message} {extra[trap]}", colorize=True)
    logger.bind(trap="<red>B</red>").opt(ansi=True).debug("<red>A</red>")
    assert writer.read() == ansimarkup.parse("<red>A</red>") + " <red>B</red>\n"


def test_ansi_with_record(writer):
    logger.add(writer, format="{message}", colorize=True)
    logger_ = logger.bind(start="<red>", end="</red>")
    logger_.opt(ansi=True, record=True).debug("{record[extra][start]}B{record[extra][end]}")
    assert writer.read() == ansimarkup.parse("<red>B</red>\n")


def test_ansi_nested(writer):
    logger.add(writer, format="(<red>[{message}]</red>)", colorize=True)
    logger.opt(ansi=True).debug("A<green>B</green>C<blue>D</blue>E")
    assert writer.read() == ansimarkup.parse("(<red>[A<green>B</green>C<blue>D</blue>E]</red>)\n")


@pytest.mark.parametrize("message", ["X </red> <red> Y", "<red>", "</red>"])
def test_ansi_raising(writer, message):
    logger.add(writer, format="<red>{message}</red>", colorize=True, catch=False)
    with pytest.raises(ansimarkup.markup.MismatchedTag):
        logger.opt(ansi=True).debug(message)


def test_ansi_with_args(writer):
    logger.add(writer, format="=> {message} <=", colorize=True)
    logger.opt(ansi=True).debug("the {0}test{end}", "<red>", end="</red>")
    assert writer.read() == ansimarkup.parse("=> the <red>test</red> <=\n")


def test_ansi_with_level(writer):
    logger.add(writer, format="{message}", colorize=True)
    logger.level("DEBUG", color="<green>")
    logger.opt(ansi=True).debug("a <level>level</level> b")
    assert writer.read() == ansimarkup.parse("a <green>level</green> b\n")


def test_ansi_double_message(writer):
    logger.add(writer, format="<red><b>{message}...</b> - <c>...{message}</c></red>", colorize=True)
    logger.opt(ansi=True).debug("<g>Double</g>")
    assert writer.read() == ansimarkup.parse(
        "<red><b><g>Double</g>...</b> - <c>...<g>Double</g></c></red>\n"
    )


def test_ansi_with_dynamic_formatter_colorized(writer):
    logger.add(writer, format=lambda r: "<red>{message}</red>", colorize=True)
    logger.opt(ansi=True).debug("<b>a</b> <y>b</y>")
    assert writer.read() == ansimarkup.parse("<red><b>a</b> <y>b</y></red>")


def test_ansi_with_dynamic_formatter_decolorized(writer):
    logger.add(writer, format=lambda r: "<red>{message}</red>", colorize=False)
    logger.opt(ansi=True).debug("<b>a</b> <y>b</y>")
    assert writer.read() == "a b"


def test_ansi_with_format_specs(writer):
    fmt = "<g>{level.no:03d} {message!s:->11} {{nope}} {extra[a][b]!r}<g>"
    logger.add(writer, colorize=False, format=fmt)
    logger.bind(a={"b": "c"}).opt(ansi=True).debug("<g>{X}</g>")
    assert writer.read() == "010 -{X} {nope} 'c'\n"


def test_ansi_with_message_specs(writer):
    logger.add(writer, colorize=False, format="<g>{message}</g>")
    logger.opt(ansi=True).debug("{} <b>A</b> {{nope}} {key:03d} {let!r}", 1, key=10, let="c")
    logger.opt(ansi=True).debug("<b>{0:0{1}d}</b>", 2, 4)
    assert writer.read() == ("1 A {nope} 010 'c'\n" "0002\n")


def test_raw(writer):
    logger.add(writer, format="", colorize=True)
    logger.opt(raw=True).info("Raw {}", "message")
    logger.opt(raw=True).log(30, " + The end")
    assert writer.read() == "Raw message + The end"


def test_raw_with_format_function(writer):
    logger.add(writer, format=lambda _: "{time} \n")
    logger.opt(raw=True).debug("Raw {message} bis", message="message")
    assert writer.read() == "Raw message bis"


def test_raw_with_ansi_colorized(writer):
    logger.add(writer, format="XYZ", colorize=True)
    logger.opt(raw=True, ansi=True).info("Raw <red>colors</red> and <lvl>level</lvl>")
    assert writer.read() == ansimarkup.parse("Raw <red>colors</red> and <b>level</b>")


def test_raw_with_ansi_decolorized(writer):
    logger.add(writer, format="XYZ", colorize=False)
    logger.opt(raw=True, ansi=True).info("Raw <red>colors</red> and <lvl>level</lvl>")
    assert writer.read() == "Raw colors and level"


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
