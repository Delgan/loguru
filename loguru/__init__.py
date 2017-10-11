import logging
from datetime import timedelta
from inspect import isclass
from logging import getLevelName, addLevelName
from os import getpid, PathLike
from os.path import normcase, basename, splitext
import sys
from sys import exc_info, stdout as STDOUT, stderr as STDERR
from multiprocessing import current_process
from threading import current_thread
from traceback import format_exception

import ansimarkup
from better_exceptions_fork import ExceptionFormatter
from pendulum import now


NOTSET = 0
TRACE = 5
DEBUG = 10
INFO = 20
SUCCESS = 25
WARNING = 30
ERROR = 40
CRITICAL = 50

addLevelName(TRACE, "TRACE")
addLevelName(SUCCESS, "SUCCESS")

LEVELS_COLORS = {
    getLevelName(TRACE): "<cyan><bold>",
    getLevelName(DEBUG): "<blue><bold>",
    getLevelName(INFO): "<bold>",
    getLevelName(SUCCESS): "<green><bold>",
    getLevelName(WARNING): "<yellow><bold>",
    getLevelName(ERROR): "<red><bold>",
    getLevelName(CRITICAL): "<RED><bold>",
}

VERBOSE_FORMAT = "<green>{time}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"

__version__ = "0.0.1"

start_time = now()

def get_frame_fallback(_):
    """Return the frame object for the caller's stack frame."""
    try:
        raise Exception
    except Exception:
        return exc_info()[2].tb_frame.f_back.f_back

def get_get_frame_function():
    if hasattr(sys, '_getframe'):
        get_frame = sys._getframe
    else:
        get_frame = get_frame_fallback
    return get_frame

get_frame = get_get_frame_function()

class Handler:

    def __init__(self, *, writter, level, format, filter, colored, better_exceptions):
        self.writter = writter
        self.level = level
        self.format = format
        self.filter = filter
        self.colored = colored
        self.better_exceptions = better_exceptions

        self.formats_per_level = self.generate_formats(format, colored)
        self.exception_formatter = ExceptionFormatter(colored=colored)

    @staticmethod
    def generate_formats(format, colored):
        formats_per_level = {}

        for level_name, level_color in LEVELS_COLORS.items():
            color = ansimarkup.parse(level_color)
            custom_markup = dict(level=color, lvl=color)
            am = ansimarkup.AnsiMarkup(tags=custom_markup)
            formats_per_level[level_name] = am.parse(format) if colored else am.strip(format)

        return formats_per_level

    # def format_exception(self, type, value, tb):
    #     ...

    # def handle(self, record):
    #     loguru_record = RecordUtils.to_loguru_record(record)
    #     self.emit(loguru_record)

    def emit(self, record, exception):
        level = record['level']
        if self.level > level.no:
            return

        if self.filter is not None:
            if not self.filter(record):
                return

        message = self.formats_per_level[level.name].format_map(record) + '\n'

        self.writter(message)
        if exception:
            if self.better_exceptions:
                for part in self.exception_formatter.format_exception(*exception):
                    self.writter(part)
            else:
                self.writter(''.join(format_exception(*exception)))


class LevelRecattr(str):
    __slots__ = ('no', 'name')


class FileRecattr(str):
    __slots__ = ('name', 'path')


class ThreadRecattr(str):
    __slots__ = ('id', 'name')


class ProcessRecattr(str):
    __slots__ = ('id', 'name')


class FileSink:

    def __init__(self, path, *, mode='a', encoding='utf8', delay=False, buffering=1):
        f = open(path, mode=mode, encoding=encoding, buffering=buffering)
        self.write = f.write


class Logger:

    def __init__(self):
        self.handlers = []

    def log_to(self, sink, *, level=DEBUG, format=VERBOSE_FORMAT, filter=None, colored=None, better_exceptions=True, **kwargs):
        if isclass(sink):
            sink = sink(**kwargs)
            return self.log_to(sink, level=level, format=format, filter=filter, colored=colored, better_exceptions=better_exceptions)
        elif callable(sink):
            if kwargs:
                writter = lambda m: sink(m, **kwargs)
            else:
                # Specialized for performances of main use case
                writter = sink
            if colored is None:
                colored = False
        elif isinstance(sink, (str, PathLike)):
            path = sink
            sink = FileSink(path, **kwargs)
            if colored is None:
                colored = False
            return self.log_to(sink, level=level, format=format, filter=filter, colored=colored, better_exceptions=better_exceptions)
        elif hasattr(sink, 'write'):
            sink_write = sink.write
            if kwargs:
                write = lambda m: sink_write(m, **kwargs)
            else:
                # Specialized for performances of main use case
                write = sink_write

            if hasattr(sink, 'flush'):
                sink_flush = sink.flush
                writter = lambda m: write(m) and sink_flush()
            else:
                writter = write

            if colored is None:
                try:
                    colored = sink.isatty()
                except Exception:
                    # The sys.stderr defined by the Python Interface to Vim doesn't
                    # have an isatty() method.
                    colored = False
        else:
            type_name = type(sink).__name__
            raise ValueError("Cannot log to objects of type '{}'.".format(type_name))

        if isinstance(filter, str):
            parent = filter + '.' * bool(filter)
            length = len(parent)
            filter = lambda r: (r['name'] + '.')[:length] == parent

        handler = Handler(
            writter=writter,
            level=level,
            format=format,
            filter=filter,
            colored=colored,
            better_exceptions=better_exceptions,
        )

        self.handlers.append(handler)

        return handler

    @staticmethod
    def make_log_function(level, log_exception=False):

        level_name = getLevelName(level)

        def log_function(self, message, *args, **kwargs):
            frame = get_frame(1)
            name = frame.f_globals['__name__']

            # TODO: Early exit if no handler

            now_ = now()
            now_._FORMATTER = 'alternative'

            message = message.format(*args, **kwargs)

            code = frame.f_code
            file_path = normcase(code.co_filename)
            file_name = basename(file_path)
            module_name = splitext(file_name)
            thread = current_thread()
            process = current_process()
            diff = now_ - start_time
            elapsed = timedelta(microseconds=diff.microseconds)

            level_recattr = LevelRecattr(level_name)
            level_recattr.no, level_recattr.name = level, level_name

            file_recattr = FileRecattr(file_name)
            file_recattr.name, file_recattr.path = file_name, file_path

            thread_recattr = ThreadRecattr(thread.ident)
            thread_recattr.id, thread_recattr.name = thread.ident, thread.name

            process_recattr = ProcessRecattr(process.ident)
            process_recattr.id, process_recattr.name = process.ident, process.name

            record = {
                'name': name,
                'message': message,
                'time': now_,
                'elapsed': elapsed,
                'line': frame.f_lineno,
                'level': level_recattr,
                'file': file_recattr,
                'function': code.co_name,
                'module': module_name,
                'thread': thread_recattr,
                'process': process_recattr,
                'frame': frame,
            }

            exception = None
            if log_exception:
                exception = exc_info()

            for handler in self.handlers:
                handler.emit(record, exception=exception)

        doc = "Log 'message.format(*args, **kwargs)' with severity '{}'.".format(level_name)
        if log_exception:
            doc += ' Log also current traceback.'
        log_function.__doc__ = doc

        return log_function

    trace = make_log_function.__func__(TRACE)
    debug = make_log_function.__func__(DEBUG)
    info = make_log_function.__func__(INFO)
    success = make_log_function.__func__(SUCCESS)
    warning = make_log_function.__func__(WARNING)
    error = make_log_function.__func__(ERROR)
    exception = make_log_function.__func__(ERROR, True)
    critical = make_log_function.__func__(CRITICAL)


logger = Logger()
logger.log_to(STDERR)
