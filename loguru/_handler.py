import functools
import json
import multiprocessing
import sys
import threading
import traceback

import ansimarkup


class StrRecord(str):
    __slots__ = ('record', )


class Handler:

    def __init__(self, *, writer, stopper, levelno, formatter, is_formatter_dynamic, filter_,
                 colored, serialized, enhanced, wrapped, queued, colors=[]):
        self.writer = writer
        self.stopper = stopper
        self.levelno = levelno
        self.formatter = formatter
        self.is_formatter_dynamic = is_formatter_dynamic
        self.filter = filter_
        self.colored = colored
        self.serialized = serialized
        self.enhanced = enhanced
        self.wrapped = wrapped
        self.queued = queued

        self.static_format = None
        self.decolorized_format = None
        self.precolorized_formats = {}

        self.lock = threading.Lock()
        self.queue = None
        self.thread = None

        if not self.is_formatter_dynamic:
            self.static_format = self.formatter
            self.decolorized_format = self.decolorize(self.static_format)

            for color in colors:
                self.update_format(color)

        if self.queued:
            self.queue = multiprocessing.SimpleQueue()
            self.thread = threading.Thread(target=self.queued_writer, daemon=True)
            self.thread.start()

    @staticmethod
    def serialize(text, record):
        exc = record["exception"]
        serializable = {
            'text': text,
            'record': {
                'elapsed': dict(repr=record['elapsed'], seconds=record['elapsed'].total_seconds()),
                'exception': exc and dict(type=exc.type.__name__, value=exc.value, traceback=bool(exc.traceback)),
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
                'time': dict(repr=record['time'], timestamp=record['time'].float_timestamp),
            }
        }

        return json.dumps(serializable, default=str) + "\n"

    @staticmethod
    def make_ansimarkup(color):
        color = ansimarkup.parse(color)
        custom_markup = dict(level=color, lvl=color)
        am = ansimarkup.AnsiMarkup(tags=custom_markup)
        return am

    @staticmethod
    @functools.lru_cache(maxsize=32)
    def decolorize(format_):
        am = Handler.make_ansimarkup('')
        return am.strip(format_)

    @staticmethod
    @functools.lru_cache(maxsize=32)
    def colorize(format_, color):
        am = Handler.make_ansimarkup(color)
        return am.parse(format_)

    def update_format(self, color):
        if self.is_formatter_dynamic or not self.colored or color in self.precolorized_formats:
            return
        self.precolorized_formats[color] = self.colorize(self.static_format, color)

    def handle_error(self, record=None):
        if not self.wrapped:
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

    def emit(self, record, level_color=None, ansi_message=False):
        try:
            if self.levelno > record['level'].no:
                return

            if self.filter is not None:
                if not self.filter(record):
                    return

            if self.is_formatter_dynamic:
                if self.colored:
                    precomputed_format = self.colorize(self.formatter(record), level_color)
                else:
                    precomputed_format = self.decolorize(self.formatter(record))
            else:
                if self.colored:
                    precomputed_format = self.precolorized_formats[level_color]
                else:
                    precomputed_format = self.decolorized_format

            error = ""
            if record['exception']:
                error = record['exception'].format_exception(self.enhanced, self.colored)
            formatter_record = {**record, **{"exception": error}}

            if ansi_message:
                message = record['message']

                if self.colored:
                    message = self.colorize(message, level_color)
                else:
                    message = self.decolorize(message)

                formatter_record['message'] = message

            formatted = precomputed_format.format_map(formatter_record)

            if self.serialized:
                formatted = self.serialize(formatted, record)

            str_record = StrRecord(formatted)
            str_record.record = record

            with self.lock:
                if self.queued:
                    self.queue.put(str_record)
                else:
                    self.writer(str_record)

        except Exception:
            self.handle_error(record)

    def queued_writer(self):
        message = None
        queue = self.queue
        try:
            while 1:
                message = queue.get()
                if message is None:
                    break
                self.writer(message)
        except Exception:
            if message and hasattr(message, 'record'):
                message = message.record
            self.handle_error(message)

    def stop(self):
        if self.queued:
            self.queue.put(None)
            self.thread.join()
        self.stopper()
