import os
import sys
from unittest.mock import MagicMock

import pytest

import loguru
from loguru import logger

from .conftest import parse


class Stream:
    def __init__(self, tty):
        self.out = ""
        self.tty = tty
        self.closed = False

    def write(self, m):
        self.out += m

    def isatty(self):
        if self.tty is None:
            raise RuntimeError
        else:
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


@pytest.fixture
def patch_colorama(monkeypatch):
    AnsiToWin32_instance = MagicMock()
    AnsiToWin32_class = MagicMock(return_value=AnsiToWin32_instance)
    winapi_test = MagicMock(return_value=True)
    win32 = MagicMock(winapi_test=winapi_test)
    colorama = MagicMock(AnsiToWin32=AnsiToWin32_class, win32=win32)
    monkeypatch.setitem(sys.modules, "colorama", colorama)
    monkeypatch.setitem(sys.modules, "colorama.win32", win32)
    yield colorama


@pytest.mark.parametrize("colorize", [True, False, None])
@pytest.mark.parametrize("tty", [True, False])
@pytest.mark.parametrize("replace_original", [True, False])
def test_colorize_stream(patch_colorama, monkeypatch, colorize, tty, replace_original):
    stream = Stream(tty)

    monkeypatch.delenv("TERM", raising=False)
    monkeypatch.delenv("PYCHARM_HOSTED", raising=False)
    monkeypatch.setattr(os, "name", "unix")
    if replace_original:
        monkeypatch.setattr(sys, "__stdout__", stream)

    logger.add(stream, format="<red>{message}</red>", colorize=colorize, catch=False)
    logger.debug("Message")

    winapi_test = patch_colorama.win32.winapi_test
    stream_write = patch_colorama.AnsiToWin32().stream.write

    assert not stream_write.called
    assert not winapi_test.called

    if colorize or (colorize is None and tty):
        assert stream.out == parse("<red>Message</red>\n")
    else:
        assert stream.out == "Message\n"


@pytest.mark.parametrize("colorize", [True, False, None])
@pytest.mark.parametrize("tty", [True, False])
@pytest.mark.parametrize("replace_original", [True, False])
def test_colorize_stream_windows(patch_colorama, monkeypatch, colorize, tty, replace_original):
    stream = Stream(tty)

    monkeypatch.delenv("TERM", raising=False)
    monkeypatch.delenv("PYCHARM_HOSTED", raising=False)
    monkeypatch.setattr(os, "name", "nt")
    if replace_original:
        monkeypatch.setattr(sys, "__stdout__", stream)

    logger.add(stream, format="<blue>{message}</blue>", colorize=colorize, catch=False)
    logger.debug("Message")

    winapi_test = patch_colorama.win32.winapi_test
    stream_write = patch_colorama.AnsiToWin32().stream.write

    if replace_original and (colorize or (colorize is None and tty)):
        assert winapi_test.called
        assert stream_write.called
    else:
        assert not winapi_test.called
        assert not stream_write.called


@pytest.mark.parametrize("colorize", [True, False, None])
def test_isatty_error(monkeypatch, colorize):
    monkeypatch.setattr(os, "name", "posix")
    stream = Stream(None)
    logger.add(stream, format="<blue>{message}</blue>", colorize=colorize)
    logger.debug("Message")

    if colorize is True:
        assert stream.out == parse("<blue>Message</blue>\n")
    else:
        assert stream.out == "Message\n"


@pytest.mark.parametrize("stream", [sys.__stdout__, sys.__stderr__])
def test_pycharm_fixed(monkeypatch, stream):
    monkeypatch.setitem(os.environ, "PYCHARM_HOSTED", "1")
    monkeypatch.setattr(stream, "isatty", lambda: False)
    assert not stream.isatty()
    assert loguru._colorama.should_colorize(stream)


@pytest.mark.parametrize("stream", [None, Stream(False), Stream(None)])
def test_pycharm_ignored(monkeypatch, stream):
    monkeypatch.setitem(os.environ, "PYCHARM_HOSTED", "1")
    assert not loguru._colorama.should_colorize(stream)


@pytest.mark.parametrize("stream", [sys.__stdout__, sys.__stderr__])
def test_mintty_fixed_windows(monkeypatch, stream):
    monkeypatch.setattr(os, "name", "nt")
    monkeypatch.setitem(os.environ, "TERM", "xterm")
    monkeypatch.setattr(stream, "isatty", lambda: False)
    assert not stream.isatty()
    assert loguru._colorama.should_colorize(stream)


@pytest.mark.parametrize("stream", [None, Stream(False), Stream(None)])
def test_mintty_ignored_windows(monkeypatch, stream):
    monkeypatch.setattr(os, "name", "nt")
    monkeypatch.setitem(os.environ, "TERM", "xterm")
    assert not loguru._colorama.should_colorize(stream)


@pytest.mark.parametrize("stream", [sys.__stdout__, sys.__stderr__])
def test_mintty_not_fixed_linux(monkeypatch, stream):
    monkeypatch.setattr(os, "name", "posix")
    monkeypatch.setitem(os.environ, "TERM", "xterm")
    monkeypatch.setattr(stream, "isatty", lambda: False)
    assert not stream.isatty()
    assert not loguru._colorama.should_colorize(stream)


@pytest.mark.parametrize("stream", [None, Stream(False), Stream(None)])
def test_mintty_ignored_linux(monkeypatch, stream):
    monkeypatch.setattr(os, "name", "posix")
    monkeypatch.setitem(os.environ, "TERM", "xterm")
    assert not loguru._colorama.should_colorize(stream)
