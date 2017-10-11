import loguru
import pytest
import sys

@pytest.fixture(autouse=True, params=['with_sys_getframe', 'without_sys_getframe'])
def with_and_without_sys_getframe(request, monkeypatch):
    if request.param == 'without_sys_getframe':
        monkeypatch.setattr(loguru, 'get_frame', loguru.get_frame_fallback)
