import sys

import loguru

def test_with_get_frame(monkeypatch):
    patched = lambda: None
    monkeypatch.setattr(sys, '_getframe', patched)
    assert loguru.get_get_frame_function() == patched

def test_without_get_frame(monkeypatch):
    monkeypatch.delattr(sys, '_getframe')
    assert loguru.get_get_frame_function() == loguru.get_frame_fallback
