import os
import sys


def should_colorize(stream):
    if stream is None:
        return False

    try:
        import ipykernel
        import IPython

        ipython = IPython.get_ipython()
        is_jupyter_stream = isinstance(stream, ipykernel.iostream.OutStream)
        is_jupyter_shell = isinstance(ipython, ipykernel.zmqshell.ZMQInteractiveShell)
    except Exception:
        pass
    else:
        if is_jupyter_stream and is_jupyter_shell:
            return True

    if stream is sys.__stdout__ or stream is sys.__stderr__:
        if "PYCHARM_HOSTED" in os.environ:
            return True
        if os.name == "nt" and "TERM" in os.environ:
            return True

    try:
        return stream.isatty()
    except Exception:
        return False


def should_wrap(stream):
    if os.name != "nt":
        return False

    if stream is not sys.__stdout__ and stream is not sys.__stderr__:
        return False

    from colorama.win32 import winapi_test

    return winapi_test()


def wrap(stream):
    from colorama import AnsiToWin32

    return AnsiToWin32(stream, convert=True, strip=False, autoreset=False).stream
