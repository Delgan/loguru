import os
import sys


def is_a_tty(stream):
    if "PYCHARM_HOSTED" in os.environ:
        if stream is not None and (stream is sys.__stdout__ or stream is sys.__stderr__):
            return True

    try:
        return stream.isatty()
    except Exception:
        return False


def should_wrap(stream):
    if os.name != "nt":
        return False

    from colorama.win32 import winapi_test

    return winapi_test()


def wrap(stream):
    from colorama import AnsiToWin32

    return AnsiToWin32(stream, convert=True, strip=False, autoreset=False).stream
