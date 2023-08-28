import os
import sys
from unittest.mock import MagicMock

import pytest

from loguru import logger
from loguru._colorama import should_colorize, should_wrap

from .conftest import StreamIsattyException, StreamIsattyFalse, StreamIsattyTrue


@pytest.fixture(autouse=True)
def clear_environment():
    env = os.environ.copy()
    os.environ.clear()
    yield
    os.environ.update(env)


@pytest.fixture
def patch_colorama(monkeypatch):
    ansi_to_win32_class = MagicMock()
    winapi_test = MagicMock(return_value=True)
    win32 = MagicMock(winapi_test=winapi_test)
    colorama = MagicMock(AnsiToWin32=ansi_to_win32_class, win32=win32)
    monkeypatch.setitem(sys.modules, "colorama", colorama)
    monkeypatch.setitem(sys.modules, "colorama.win32", win32)
    yield colorama


@pytest.mark.parametrize("patched", ["__stdout__", "__stderr__"])
@pytest.mark.skipif(os.name != "nt", reason="Only Windows requires Colorama")
def test_stream_wrapped_on_windows(patched, monkeypatch, patch_colorama):
    stream = StreamIsattyTrue()
    monkeypatch.setattr(sys, patched, stream, raising=False)
    patch_colorama.win32.winapi_test.return_value = True
    logger.add(stream, colorize=True)
    assert patch_colorama.AnsiToWin32.called


def test_stream_is_none():
    assert not should_colorize(None)


def test_is_a_tty():
    assert should_colorize(StreamIsattyTrue())


def test_is_not_a_tty():
    assert not should_colorize(StreamIsattyFalse())


def test_is_a_tty_exception():
    assert not should_colorize(StreamIsattyException())


@pytest.mark.parametrize(
    "patched, expected",
    [
        ("__stdout__", True),
        ("__stderr__", True),
        ("stdout", False),
        ("stderr", False),
        ("", False),
    ],
)
def test_pycharm_fixed(monkeypatch, patched, expected):
    stream = StreamIsattyFalse()
    monkeypatch.setattr(sys, patched, stream, raising=False)
    monkeypatch.setitem(os.environ, "PYCHARM_HOSTED", "1")
    assert should_colorize(stream) is expected


@pytest.mark.parametrize(
    "patched, expected",
    [
        ("__stdout__", True),
        ("__stderr__", True),
        ("stdout", False),
        ("stderr", False),
        ("", False),
    ],
)
def test_github_actions_fixed(monkeypatch, patched, expected):
    stream = StreamIsattyFalse()
    monkeypatch.setitem(os.environ, "CI", "1")
    monkeypatch.setitem(os.environ, "GITHUB_ACTIONS", "1")
    monkeypatch.setattr(sys, patched, stream, raising=False)
    assert should_colorize(stream) is expected


@pytest.mark.parametrize(
    "patched, expected",
    [
        ("__stdout__", True),
        ("__stderr__", True),
        ("stdout", False),
        ("stderr", False),
        ("", False),
    ],
)
@pytest.mark.skipif(os.name != "nt", reason="The fix is applied only on Windows")
def test_mintty_fixed_windows(monkeypatch, patched, expected):
    stream = StreamIsattyFalse()
    monkeypatch.setitem(os.environ, "TERM", "xterm")
    monkeypatch.setattr(sys, patched, stream, raising=False)
    assert should_colorize(stream) is expected


@pytest.mark.parametrize(
    "patched, expected",
    [
        ("__stdout__", False),
        ("__stderr__", False),
        ("stdout", False),
        ("stderr", False),
        ("", False),
    ],
)
@pytest.mark.skipif(os.name == "nt", reason="The fix will be applied on Windows")
def test_mintty_not_fixed_linux(monkeypatch, patched, expected):
    stream = StreamIsattyFalse()
    monkeypatch.setitem(os.environ, "TERM", "xterm")
    monkeypatch.setattr(sys, patched, stream, raising=False)
    assert should_colorize(stream) is expected


@pytest.mark.parametrize(
    "patched, out_class, expected",
    [
        ("stdout", StreamIsattyFalse, True),
        ("stderr", StreamIsattyFalse, True),
        ("__stdout__", StreamIsattyFalse, False),
        ("__stderr__", StreamIsattyFalse, False),
        ("stdout", StreamIsattyTrue, False),
        ("stderr", StreamIsattyTrue, False),
        ("", StreamIsattyFalse, False),
    ],
)
def test_jupyter_fixed(monkeypatch, patched, out_class, expected):
    stream = StreamIsattyFalse()

    class Shell:
        pass

    ipython = MagicMock()
    ipykernel = MagicMock()
    instance = MagicMock()
    instance.__class__ = Shell
    ipython.get_ipython.return_value = instance
    ipykernel.zmqshell.ZMQInteractiveShell = Shell
    ipykernel.iostream.OutStream = out_class

    monkeypatch.setitem(sys.modules, "IPython", ipython)
    monkeypatch.setitem(sys.modules, "ipykernel", ipykernel)
    monkeypatch.setattr(sys, patched, stream, raising=False)

    assert should_colorize(stream) is expected


@pytest.mark.parametrize("patched", ["__stdout__", "__stderr__"])
@pytest.mark.skipif(os.name == "nt", reason="Colorama is required on Windows")
def test_dont_wrap_on_linux(monkeypatch, patched, patch_colorama):
    stream = StreamIsattyTrue()
    monkeypatch.setattr(sys, patched, stream, raising=False)
    assert not should_wrap(stream)
    assert not patch_colorama.win32.winapi_test.called


@pytest.mark.parametrize("patched", ["stdout", "stderr", ""])
@pytest.mark.skipif(os.name != "nt", reason="Only Windows requires Colorama")
def test_dont_wrap_if_not_stdout_or_stderr(monkeypatch, patched, patch_colorama):
    stream = StreamIsattyTrue()
    monkeypatch.setattr(sys, patched, stream, raising=False)
    assert not should_wrap(stream)
    assert not patch_colorama.win32.winapi_test.called


@pytest.mark.parametrize("patched", ["__stdout__", "__stderr__"])
@pytest.mark.skipif(os.name != "nt", reason="Only Windows requires Colorama")
def test_dont_wrap_if_winapi_false(monkeypatch, patched, patch_colorama):
    stream = StreamIsattyTrue()
    monkeypatch.setattr(sys, patched, stream, raising=False)
    patch_colorama.win32.winapi_test.return_value = False
    assert not should_wrap(stream)
    assert patch_colorama.win32.winapi_test.called


@pytest.mark.parametrize("patched", ["__stdout__", "__stderr__"])
@pytest.mark.skipif(os.name != "nt", reason="Only Windows requires Colorama")
def test_wrap_if_winapi_true(monkeypatch, patched, patch_colorama):
    stream = StreamIsattyTrue()
    monkeypatch.setattr(sys, patched, stream, raising=False)
    patch_colorama.win32.winapi_test.return_value = True
    assert should_wrap(stream)
    assert patch_colorama.win32.winapi_test.called
