import importlib
import sys

import loguru


def test_with_sys_getframe(monkeypatch):
    def patched():
        return

    monkeypatch.setattr(sys, "_getframe", patched())
    get_frame_module = importlib.reload(loguru._get_frame)
    assert get_frame_module.get_frame == patched()


def test_without_sys_getframe(monkeypatch):
    monkeypatch.delattr(sys, "_getframe")
    get_frame_module = importlib.reload(loguru._get_frame)
    assert get_frame_module.get_frame == loguru._get_frame.get_frame_fallback


def test_get_frame_fallback():
    frame_root = frame_a = frame_b = None

    def a():
        nonlocal frame_a
        frame_a = loguru._get_frame.get_frame_fallback(1)
        b()

    def b():
        nonlocal frame_b
        frame_b = loguru._get_frame.get_frame_fallback(2)

    frame_root = loguru._get_frame.get_frame_fallback(0)
    a()

    assert frame_a == frame_b == frame_root
