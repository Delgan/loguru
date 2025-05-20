import re

import pytest

from loguru import logger


def test_patch_after_add(writer):
    logger.add(writer, format="{extra[a]} {message}")
    logger_patched = logger.patch(lambda r: r["extra"].update(a=0))
    logger_patched.debug("A")

    assert writer.read() == "0 A\n"


def test_patch_before_add(writer):
    logger_patched = logger.patch(lambda r: r["extra"].update(a=0))
    logger.add(writer, format="{extra[a]} {message}")
    logger_patched.debug("A")

    assert writer.read() == "0 A\n"


def test_add_using_patched(writer):
    logger.configure(patcher=lambda r: r["extra"].update(a=-1))
    logger_patched = logger.patch(lambda r: r["extra"].update(a=0))
    logger_patched.add(writer, format="{extra[a]} {message}")
    logger.debug("A")
    logger_patched.debug("B")

    assert writer.read() == "-1 A\n0 B\n"


def test_not_override_parent_logger(writer):
    logger_1 = logger.patch(lambda r: r["extra"].update(a="a"))
    logger_2 = logger_1.patch(lambda r: r["extra"].update(a="A"))
    logger.add(writer, format="{extra[a]} {message}")

    logger_1.debug("1")
    logger_2.debug("2")

    assert writer.read() == "a 1\nA 2\n"


def test_override_previous_patched(writer):
    logger.add(writer, format="{extra[x]} {message}")
    logger2 = logger.patch(lambda r: r["extra"].update(x=3))
    logger2.patch(lambda r: r["extra"].update(x=2)).debug("4")
    assert writer.read() == "2 4\n"


def test_no_conflict(writer):
    logger_ = logger.patch(lambda r: None)
    logger_2 = logger_.patch(lambda r: r["extra"].update(a=2))
    logger_3 = logger_.patch(lambda r: r["extra"].update(a=3))

    logger.add(writer, format="{extra[a]} {message}")

    logger_2.debug("222")
    logger_3.debug("333")

    assert writer.read() == "2 222\n3 333\n"


def test_override_configured(writer):
    logger.configure(patcher=lambda r: r["extra"].update(a=123, b=678))
    logger2 = logger.patch(lambda r: r["extra"].update(a=456))

    logger2.add(writer, format="{extra[a]} {extra[b]} {message}")

    logger2.debug("!")

    assert writer.read() == "456 678 !\n"


def test_multiple_patches(writer):
    def patch_1(record):
        record["extra"]["a"] = 5

    def patch_2(record):
        record["extra"]["a"] += 1

    def patch_3(record):
        record["extra"]["a"] *= 2

    logger.add(writer, format="{extra[a]} {message}")
    logger.patch(patch_1).patch(patch_2).patch(patch_3).info("Test")

    assert writer.read() == "12 Test\n"


@pytest.mark.parametrize(
    ("colorize", "colors", "expected"),
    [
        (False, False, "<red>A</red>\n"),
        (False, True, "A\n"),
        (True, False, "<red>A</red>\n"),
        (True, True, "\x1b[31mA\x1b[0m\n"),
    ],
)
def test_colorful_patch(colorize, colors, expected, writer):
    logger.add(writer, format="{message}", colorize=colorize)

    logger_patched = logger.patch(lambda r: r.update(message=f"<red>{r['message']}</red>"))
    logger_patched.opt(colors=colors).debug("A")

    assert writer.read() == expected


@pytest.mark.parametrize(
    ("colorize", "colors", "expected"),
    [
        (False, False, "A <red>W</red>, <red>M</red>\n"),
        (False, True, "A W, M\n"),
        (True, False, "A <red>W</red>, <red>M</red>\n"),
        (True, True, "A \x1b[31mW\x1b[0m, \x1b[31mM\x1b[0m\n"),
    ],
)
def test_automatic_colorful_patch(colorize, colors, expected, writer):
    # regex matches on single curly braces and substitutes
    # a color tag in-place
    _regex_pattern = re.compile(r"(\{[^{}]*\})(?!\})")
    _regex_repl = r"<red>\1</red>"

    def patch(r):
        r.update(message=re.sub(_regex_pattern, _regex_repl, r["message"]))

    logger.add(writer, format="{message}", colorize=colorize)
    logger_patched = logger.patch(patch)
    logger_patched.opt(colors=colors).debug("A {}, {a}", "W", a="M")

    assert writer.read() == expected
