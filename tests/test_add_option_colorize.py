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
    "message, format, expected, colorize",
    [
        ("a", "<red>{message}</red>", "a\n", False),
        ("b", "<red>{message}</red>", parse("<red>b</red>\n"), True),
        ("c", lambda _: "<red>{message}</red>", "c", False),
        ("d", lambda _: "<red>{message}</red>", parse("<red>d</red>"), True),
        ("<red>nope</red>", "{message}", "<red>nope</red>\n", True),
    ],
)
def test_colorize(message, format, expected, colorize, writer):
    logger.add(writer, format=format, colorize=colorize)
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
