import re
import sys
import traceback
from collections import namedtuple

from better_exceptions_fork import ExceptionFormatter

loguru_traceback = namedtuple("loguru_traceback", ("tb_frame", "tb_lasti", "tb_lineno", "tb_next"))


loguru_frame = namedtuple(
    "loguru_frame",
    ("f_back", "f_builtins", "f_code", "f_globals", "f_lasti", "f_lineno", "f_locals", "f_trace"),
)


loguru_code = namedtuple(
    "loguru_code",
    (
        "co_argcount",
        "co_code",
        "co_cellvars",
        "co_consts",
        "co_filename",
        "co_firstlineno",
        "co_flags",
        "co_lnotab",
        "co_freevars",
        "co_kwonlyargcount",
        "co_name",
        "co_names",
        "co_nlocals",
        "co_stacksize",
        "co_varnames",
    ),
)


class LevelRecattr(str):
    __slots__ = ("name", "no", "icon")


class FileRecattr(str):
    __slots__ = ("name", "path")


class ThreadRecattr(str):
    __slots__ = ("name", "id")


class ProcessRecattr(str):
    __slots__ = ("name", "id")


class ExceptionRecattr:

    _catch_point_identifier = " <Loguru catch point here>"

    def __init__(self, exception, decorated):
        if isinstance(exception, BaseException):
            type_, value, traceback = (type(exception), exception, exception.__traceback__)
        elif isinstance(exception, tuple):
            type_, value, traceback = exception
        else:
            type_, value, traceback = sys.exc_info()

        self.type = type_
        self.value = value
        self.traceback = traceback

        if traceback:
            self._extended_traceback = self._extend_traceback(traceback, decorated)
        else:
            self._extended_traceback = None

    def __reduce__(self):
        exception = (self.type, self.value, None)  # tracebacks are not pickable
        args = (exception, None)
        return (ExceptionRecattr, args)

    def _extend_traceback(self, tb, decorated):
        frame = tb.tb_frame

        if decorated:
            bad_frame = (tb.tb_frame.f_code.co_filename, tb.tb_frame.f_lineno)
            tb = tb.tb_next
            caught = False
        else:
            bad_frame = None
            tb = self._make_catch_traceback(tb.tb_frame, tb.tb_lasti, tb.tb_lineno, tb.tb_next)
            caught = True

        while True:
            frame = frame.f_back

            if not frame:
                break

            if (frame.f_code.co_filename, frame.f_lineno) == bad_frame:
                continue

            if not caught:
                caught = True
                tb = self._make_catch_traceback(frame, frame.f_lasti, frame.f_lineno, tb)
            else:
                tb = loguru_traceback(frame, frame.f_lasti, frame.f_lineno, tb)

        return tb

    def _make_catch_traceback(self, frame, lasti, lineno, next_):
        f = frame
        c = frame.f_code
        code = loguru_code(
            c.co_argcount,
            c.co_code,
            c.co_cellvars,
            c.co_consts,
            c.co_filename,
            c.co_firstlineno,
            c.co_flags,
            c.co_lnotab,
            c.co_freevars,
            c.co_kwonlyargcount,
            c.co_name + self._catch_point_identifier,
            c.co_names,
            c.co_nlocals,
            c.co_stacksize,
            c.co_varnames,
        )
        frame = loguru_frame(
            f.f_back, f.f_builtins, code, f.f_globals, f.f_lasti, f.f_lineno, f.f_locals, f.f_trace
        )
        tb = loguru_traceback(frame, lasti, lineno, next_)
        return tb

    def _format_catch_point(self, error):
        regex = r".*%s.*" % re.escape(self._catch_point_identifier)

        def replace(match):
            return match.group(0).replace(" ", ">", 1).replace(self._catch_point_identifier, "")

        return re.sub(regex, replace, error, re.MULTILINE)

    def format_exception(self, backtrace, colored, encoding):
        type_, value, ex_traceback = self.type, self.value, self._extended_traceback

        if not backtrace:
            error = traceback.format_exception(type_, value, ex_traceback)
        elif colored:
            formatter = ExceptionFormatter(colored=True, encoding=encoding)
            error = formatter.format_exception(type_, value, ex_traceback)
        else:
            formatter = ExceptionFormatter(colored=False, encoding=encoding)
            error = formatter.format_exception(type_, value, ex_traceback)

        error = "".join(error)

        return self._format_catch_point(error)
