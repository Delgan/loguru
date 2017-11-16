import sys
from sys import exc_info


def getframe_fallback(n):
    """Return the frame object for the caller's stack frame."""
    try:
        raise Exception
    except Exception:
        frame = exc_info()[2].tb_frame.f_back
        for _ in range(n):
            frame = frame.f_back
        return frame


def get_getframe_function():
    if hasattr(sys, '_getframe'):
        getframe = sys._getframe
    else:
        getframe = getframe_fallback
    return getframe


getframe = get_getframe_function()
