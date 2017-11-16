import random
import re
import traceback

import ansimarkup
from better_exceptions_fork import ExceptionFormatter


class HackyInt(int):

    rand = '0' + str(random.randrange(10**32, 10**33))

    def __str__(self):
        return self.rand

    def __eq__(self, other):
        return False


class StrRecord(str):
    pass


class Handler:

    def __init__(self, *, writer, levelno, format_, filter_, colored, better_exceptions, colors=[]):
        self.writer = writer
        self.levelno = levelno
        self.format = format_
        self.filter = filter_
        self.colored = colored
        self.better_exceptions = better_exceptions
        self.decolorized_format = self.decolorize(format_)
        self.precolorized_formats = {}

        if colored:
            for color in colors:
                self.update_format(color)

        self.exception_formatter = ExceptionFormatter(colored=colored)

    @staticmethod
    def make_ansimarkup(color):
        color = ansimarkup.parse(color)
        custom_markup = dict(level=color, lvl=color)
        am = ansimarkup.AnsiMarkup(tags=custom_markup)
        return am

    @staticmethod
    def decolorize(format_):
        am = Handler.make_ansimarkup('')
        return am.strip(format_)

    @staticmethod
    def colorize(format_, color):
        am = Handler.make_ansimarkup(color)
        return am.parse(format_)

    def update_format(self, color):
        if not self.colored or color in self.precolorized_formats:
            return
        self.precolorized_formats[color] = self.colorize(self.format, color)

    def emit(self, record, exception=None, level_color=None):
        level = record['level']
        if self.levelno > level.no:
            return

        if self.filter is not None:
            if not self.filter(record):
                return

        if self.colored:
            precomputed_format = self.precolorized_formats[level_color]
        else:
            precomputed_format = self.decolorized_format

        formatted = precomputed_format.format_map(record) + '\n'

        if exception:
            hacky_int = None
            tb = exception[2]
            while tb:
                if tb.__is_caught_point__:
                    hacky_int = HackyInt(tb.tb_lineno)
                    tb.tb_lineno = hacky_int
                    break
                tb = tb.tb_next

            if self.better_exceptions:
                formatted_exc = self.exception_formatter.format_exception(*exception)
            else:
                formatted_exc = traceback.format_exception(*exception)

            formatted_exc = ''.join(formatted_exc)

            reg = r'(?:^\S*(Traceback \(most recent call last\):)\S*$|^\S*  \S*File.*\D(%s)\D.*$)' % str(hacky_int)
            matches = re.finditer(reg, formatted_exc, flags=re.M)

            tb_match = None

            for match in matches:
                tb, line = match.groups()
                if tb is not None:
                    tb_match = match
                if line is not None:
                    s, e = match.span(2)
                    formatted_exc = formatted_exc[:s] + str(int(hacky_int)) + formatted_exc[e:]
                    s = match.start(0)
                    formatted_exc = formatted_exc[:s] + formatted_exc[s:].replace(" ", ">", 1)
                    if tb_match is not None:
                        old = "Traceback (most recent call last):"
                        new = "Traceback (most recent call last, catch point marked):"
                        s = tb_match.start(0)
                        formatted_exc = formatted_exc[:s] + formatted_exc[s:].replace(old, new, 1)
                    break

            formatted += formatted_exc

        message = StrRecord(formatted)
        message.record = record

        self.writer(message)
