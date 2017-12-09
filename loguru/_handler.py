import json
import multiprocessing
import threading
import random
import re
import sys
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
    __slots__ = ('record', 'exception')


class Handler:

    def __init__(self, *, writer, stopper, levelno, format_, filter_, colored, structured, enhanced, guarded, catched, colors=[]):
        self.writer = writer
        self.stopper = stopper
        self.levelno = levelno
        self.format = format_
        self.filter = filter_
        self.colored = colored
        self.structured = structured
        self.enhanced = enhanced
        self.catched = catched
        self.decolorized_format = self.decolorize(format_)
        self.precolorized_formats = {}
        self.lock = multiprocessing.Lock() if guarded else threading.Lock()

        if colored:
            for color in colors:
                self.update_format(color)

        self.exception_formatter = ExceptionFormatter(colored=colored)

    @staticmethod
    def serialize(formatted_message, record, exception):
        if exception:
            etype, value, _ = exception
            exception = traceback.format_exception_only(etype, value)

        serializable = {
            'exception': exception,
            'formatted_message': formatted_message,
            'record': {
                'elapsed': record['elapsed'].total_seconds(),
                'extra': record['extra'],
                'file': dict(name=record['file'].name, path=record['file'].path),
                'function': record['function'],
                'level': dict(icon=record['level'].icon, name=record['level'].name, no=record['level'].no),
                'line': record['line'],
                'message': record['message'],
                'module': record['module'],
                'name': record['name'],
                'process': dict(id=record['process'].id, name=record['process'].name),
                'thread': dict(id=record['thread'].id, name=record['thread'].name),
                'time': record['time'].float_timestamp,
            }
        }

        return json.dumps(serializable, default=str)

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
        try:
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

                if self.enhanced:
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

            if self.structured:
                formatted = self.serialize(formatted, record, exception) + '\n'

            message = StrRecord(formatted)
            message.record = record
            message.exception = exception

            with self.lock:
                self.writer(message)

        except Exception:
            if not self.catched:
                raise

            if not sys.stderr:
                return

            ex_type, ex, tb = sys.exc_info()

            try:
                sys.stderr.write('--- Logging error in Loguru ---\n')
                sys.stderr.write('Record was: ')
                try:
                    sys.stderr.write(str(record))
                except Exception:
                    sys.stderr.write('/!\\ Unprintable record /!\\')
                sys.stderr.write('\n')
                traceback.print_exception(ex_type, ex, tb, None, sys.stderr)
                sys.stderr.write('--- End of logging error ---\n')
            except OSError:
                pass
            finally:
                del ex_type, ex, tb

    def stop(self):
        self.stopper()
