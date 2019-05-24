import pytest
from unittest.mock import MagicMock
from loguru import logger
from loguru._ansimarkup import AnsiMarkup
import colorama


def parse(text):
    return AnsiMarkup(strip=False).feed(text, strict=True)


class Stream:
    def __init__(self, tty):
        self.out = ""
        self.tty = tty

    def write(self, m):
        self.out += m

    def isatty(self):
        return self.tty

    def flush(self):
        pass


@pytest.mark.parametrize(
    "format, message, expected",
    [
        ("<red>{message}</red>", "Foo", parse("<red>Foo</red>\n")),
        (lambda _: "<red>{message}</red>", "Bar", parse("<red>Bar</red>")),
        ("{message}", "<red>Baz</red>", "<red>Baz</red>\n"),
        ("{{<red>{message:}</red>}}", "A", parse("{<red>A</red>}\n")),
    ],
)
def test_colorized_format(format, message, expected, writer):
    logger.add(writer, format=format, colorize=True)
    logger.debug(message)
    assert writer.read() == expected


@pytest.mark.parametrize(
    "format, message, expected",
    [
        ("<red>{message}</red>", "Foo", "Foo\n"),
        (lambda _: "<red>{message}</red>", "Bar", "Bar"),
        ("{message}", "<red>Baz</red>", "<red>Baz</red>\n"),
        ("{{<red>{message:}</red>}}", "A", "{A}\n"),
    ],
)
def test_decolorized_format(format, message, expected, writer):
    logger.add(writer, format=format, colorize=False)
    logger.debug(message)
    assert writer.read() == expected


@pytest.mark.parametrize("colorize", [True, False, None])
@pytest.mark.parametrize("tty", [True, False])
def test_colorize_stream_linux(monkeypatch, colorize, tty):
    mock = MagicMock()
    monkeypatch.setattr(colorama.AnsiToWin32, "should_wrap", lambda _: False)
    monkeypatch.setattr(colorama.AnsiToWin32, "write", mock)
    stream = Stream(tty)
    logger.add(stream, format="<red>{message}</red>", colorize=colorize)
    logger.debug("Message")
    out = stream.out

    assert not mock.called

    if colorize or (colorize is None and tty):
        assert out == parse("<red>Message</red>\n")
    else:
        assert out == "Message\n"


@pytest.mark.parametrize("colorize", [True, False, None])
@pytest.mark.parametrize("tty", [True, False])
def test_auto_colorize_stream_windows(monkeypatch, colorize, tty):
    mock = MagicMock()
    monkeypatch.setattr(colorama.AnsiToWin32, "should_wrap", lambda _: True)
    monkeypatch.setattr(colorama.AnsiToWin32, "write", mock)
    stream = Stream(tty)
    logger.add(stream, format="<blue>{message}</blue>", colorize=colorize)
    logger.debug("Message")

    if colorize or (colorize is None and tty):
        assert mock.called
    else:
        assert not mock.called


@pytest.mark.parametrize("colorize", [True, False, None])
@pytest.mark.parametrize("tty", [True, False])
def test_auto_colorize_bugged_stream(monkeypatch, colorize, tty):
    def bugged(*a, **k):
        raise RuntimeError

    mock = MagicMock()
    monkeypatch.setattr(colorama.AnsiToWin32, "__init__", bugged)
    stream = Stream(tty)
    logger.add(stream, format="<green>{message}</green>", colorize=colorize)
    monkeypatch.setattr(colorama.AnsiToWin32, "write", mock)
    logger.debug("No error")
    out = stream.out

    assert not mock.called

    if colorize:
        assert out == parse("<green>No error</green>\n")
    else:
        assert out == "No error\n"
