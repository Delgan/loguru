import random
import re
import sys
import traceback

from better_exceptions_fork import ExceptionFormatter


class HackyInt(int):

    rand = "{:0>32}".format(random.randrange(10**31))

    def __str__(self):
        return self.rand

    def __eq__(self, other):
        return False


class loguru_traceback:
    __slots__ = ('tb_frame', 'tb_lasti', 'tb_lineno', 'tb_next', '__is_caught_point__')

    def __init__(self, frame, lasti, lineno, next_=None, is_caught_point=False):
        self.tb_frame = frame
        self.tb_lasti = lasti
        self.tb_lineno = lineno
        self.tb_next = next_
        self.__is_caught_point__ = is_caught_point


class LevelRecattr(str):
    __slots__ = ('name', 'no', 'icon')


class FileRecattr(str):
    __slots__ = ('name', 'path')


class ThreadRecattr(str):
    __slots__ = ('name', 'id')


class ProcessRecattr(str):
    __slots__ = ('name', 'id')


class ExceptionRecattr:

    exception_formatter_colored = ExceptionFormatter(colored=True)
    exception_formatter_not_colored = ExceptionFormatter(colored=False)

    def __init__(self, exception, decorated):
        if isinstance(exception, BaseException):
            type_, value, traceback = type(exception), exception, exception.__traceback__
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
        if decorated:
            bad_frame = (tb.tb_frame.f_code.co_filename, tb.tb_frame.f_lineno)
            tb = tb.tb_next

        root_frame = tb.tb_frame.f_back

        loguru_tracebacks = []
        while tb:
            loguru_tb = loguru_traceback(tb.tb_frame, tb.tb_lasti, tb.tb_lineno, None)
            loguru_tracebacks.append(loguru_tb)
            tb = tb.tb_next

        for prev_tb, next_tb in zip(loguru_tracebacks, loguru_tracebacks[1:]):
            prev_tb.tb_next = next_tb

        # root_tb
        tb = loguru_tracebacks[0] if loguru_tracebacks else None
        frames = []
        while root_frame:
            frames.insert(0, root_frame)
            root_frame = root_frame.f_back

        if decorated:
            frames = [f for f in frames if (f.f_code.co_filename, f.f_lineno) != bad_frame]
            caught_tb = None
        else:
            caught_tb = tb

        for f in reversed(frames):
            tb = loguru_traceback(f, f.f_lasti, f.f_lineno, tb)
            if decorated and caught_tb is None:
                caught_tb = tb

        if caught_tb:
            caught_tb.__is_caught_point__ = True

        return tb

    def format_exception(self, enhanced, colored):
        type_, value, tb = self.type, self.value, self._extended_traceback

        hacky_int = None
        tb_ = tb

        while tb_:
            if tb_.__is_caught_point__:
                hacky_int = HackyInt(tb_.tb_lineno)
                tb_.tb_lineno = hacky_int
                break
            tb_ = tb_.tb_next

        if not enhanced:
            error = traceback.format_exception(type_, value, tb)
        elif colored:
            error = self.exception_formatter_colored.format_exception(type_, value, tb)
        else:
            error = self.exception_formatter_not_colored.format_exception(type_, value, tb)

        error = ''.join(error)

        reg = r'(?:^\S*(Traceback \(most recent call last\):)\S*$|^\S*  \S*File.*\D(%s)\D.*$)' % str(hacky_int)
        matches = re.finditer(reg, error, flags=re.M)

        tb_match = None

        for match in matches:
            tb, line = match.groups()
            if tb is not None:
                tb_match = match
            if line is not None:
                s, e = match.span(2)
                error = error[:s] + str(int(hacky_int)) + error[e:]
                s = match.start(0)
                error = error[:s] + error[s:].replace(" ", ">", 1)
                if tb_match is not None:
                    old = "Traceback (most recent call last):"
                    new = "Traceback (most recent call last, catch point marked):"
                    s = tb_match.start(0)
                    error = error[:s] + error[s:].replace(old, new, 1)
                break

        return error
