import atexit
import functools
import itertools
import string
from inspect import isclass
from multiprocessing import current_process
from os import PathLike
from os.path import basename, normcase, splitext
from sys import exc_info
from threading import current_thread

import pendulum
from pendulum import now as pendulum_now

from ._catcher import Catcher
from ._file_sink import FileSink
from ._getframe import getframe
from ._handler import Handler

VERBOSE_FORMAT = "<green>{time}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"

start_time = pendulum_now()

_format_field = string.Formatter.format_field


class EscapingFormatter(string.Formatter):

    def format_field(self, value, spec):
        return _format_field(self, value, spec).replace("{", "{{").replace("}", "}}")


class loguru_traceback:
    __slots__ = ('tb_frame', 'tb_lasti', 'tb_lineno', 'tb_next', '__is_caught_point__')

    def __init__(self, frame, lasti, lineno, next_=None, is_caught_point=False):
        self.tb_frame = frame
        self.tb_lasti = lasti
        self.tb_lineno = lineno
        self.tb_next = next_
        self.__is_caught_point__ = is_caught_point


class LevelRecattr(str):
    __slots__ = ('no', 'name', 'icon')


class FileRecattr(str):
    __slots__ = ('name', 'path')


class ThreadRecattr(str):
    __slots__ = ('id', 'name')


class ProcessRecattr(str):
    __slots__ = ('id', 'name')


class Logger:

    def __init__(self):
        self._handlers_count = itertools.count()
        self._handlers = {}
        self._levels = {}
        self.catch = Catcher(self)
        self.extra = {}

        self._init_levels()
        atexit.register(self.stop)

    def bind(self, **kwargs):
        # For performance reasons, it does not return an actual wrapper
        # But user does not have to know implementation details
        # The key is that each attribute have to be a reference, so loggers share same handlers and levels
        logger = Logger.__new__(Logger)
        logger._handlers_count = self._handlers_count
        logger._handlers = self._handlers
        logger._levels = self._levels
        logger.catch = self.catch
        logger.extra = {**self.extra, **kwargs}
        return logger

    def add_level(self, name, level, color="", icon=" "):
        if not isinstance(name, str):
            raise ValueError("Invalid level name, it should be a string, not: '%s'" % type(name).__name__)

        if not isinstance(level, int):
            raise ValueError("Invalid level value, it should be an int, not: '%s'" % type(level).__name__)

        if level < 0:
            raise ValueError("Invalid level value (%d), it should be a positive number" % level)

        self._levels[name] = (level, color, icon)

        for handler in self._handlers.values():
            handler.update_format(color)


    def edit_level(self, name, level=None, color=None, icon=None):
        old_level, old_color, old_icon = self.get_level(name)

        if level is None:
            level = old_level

        if color is None:
            color = old_color

        if icon is None:
            icon = old_icon

        self.add_level(name, level, color, icon)

    def get_level(self, name):
        return self._levels[name]

    def _init_levels(self):
        self.add_level("TRACE", 5, "<cyan><bold>", "✏️")        # Pencil
        self.add_level("DEBUG", 10, "<blue><bold>", "🐞")        # Lady Beetle
        self.add_level("INFO", 20, "<bold>", "ℹ️")                # Information
        self.add_level("SUCCESS", 25, "<green><bold>", "✔️")   # Heavy Check Mark
        self.add_level("WARNING", 30, "<yellow><bold>", "⚠️")  # Warning
        self.add_level("ERROR", 40, "<red><bold>", "❌")          # Cross Mark
        self.add_level("CRITICAL", 50, "<RED><bold>", "☠️")   # Skull and Crossbones

    def reset(self):
        self.stop()
        self.extra.clear()
        self._levels.clear()
        self._init_levels()

    def start(self, sink, *, level="DEBUG", format=VERBOSE_FORMAT, filter=None, colored=None, structured=False, better_exceptions=True, **kwargs):
        if colored is None and structured is True:
            colored = False

        if isclass(sink):
            sink = sink(**kwargs)
            return self.start(sink, level=level, format=format, filter=filter, colored=colored, structured=structured, better_exceptions=better_exceptions)
        elif callable(sink):
            if kwargs:
                writer = lambda m: sink(m, **kwargs)
            else:
                writer = sink
            stopper = lambda: None
            if colored is None:
                colored = False
        elif isinstance(sink, (str, PathLike)):
            path = sink
            sink = FileSink(path, **kwargs)
            return self.start(sink, level=level, format=format, filter=filter, colored=colored, structured=structured, better_exceptions=better_exceptions)
        elif hasattr(sink, 'write') and callable(sink.write):
            sink_write = sink.write
            if kwargs:
                write = lambda m: sink_write(m, **kwargs)
            else:
                write = sink_write

            if hasattr(sink, 'flush') and callable(sink.flush):
                sink_flush = sink.flush
                writer = lambda m: write(m) and sink_flush()
            else:
                writer = write

            if hasattr(sink, 'stop') and callable(sink.stop):
                stopper = sink.stop
            else:
                stopper = lambda: None

            if colored is None:
                try:
                    colored = sink.isatty()
                except Exception:
                    colored = False
        else:
            raise ValueError("Cannot log to objects of type '%s'." % type(sink).__name__)

        if isinstance(filter, str):
            parent = filter + '.' * bool(filter)
            length = len(parent)
            filter = lambda r: (r['name'] + '.')[:length] == parent

        if isinstance(level, str):
            levelno, _, _ = self._levels[level]
        elif isinstance(level, int):
            levelno = level
        else:
            raise ValueError("Invalid level, it should be an int or a string, not: '%s'" % type(level).__name__)

        if levelno < 0:
            raise ValueError("Invalid level value (%d), it should be a positive number" % levelno)

        handler = Handler(
            writer=writer,
            stopper=stopper,
            levelno=levelno,
            format_=format,
            filter_=filter,
            colored=colored,
            structured=structured,
            better_exceptions=better_exceptions,
            colors=[color for _, color, _ in self._levels.values()] + [''],
        )

        handlers_count = next(self._handlers_count)
        self._handlers[handlers_count] = handler

        return handlers_count

    def stop(self, handler_id=None):
        if handler_id is None:
            for handler in self._handlers.values():
                handler.stop()
            count = len(self._handlers)
            self._handlers.clear()
            return count
        elif handler_id in self._handlers:
            handler = self._handlers.pop(handler_id)
            handler.stop()
            return 1
        return 0

    def configure(self, config):
        self.extra.update(config.get('extra', {}))
        for params in config.get('levels', []):
            self.add_level(**params)
        handlers_ids = [self.start(**params) for params in config.get('sinks', [])]
        return handlers_ids

    def log(_self, _level, _message, *args, **kwargs):
        _self._log(_level, False, 3, False, _message, *args, **kwargs)

    def log_exception(_self, _level, _message, *args, **kwargs):
        _self._log(_level, True, 3, False, _message, *args, **kwargs)

    def _log(_self, _level, _log_exception, _frame_idx, _decorated, _message, *args, **kwargs):
        function = _self.make_log_function(level=_level,
                                           log_exception=_log_exception,
                                           frame_idx=_frame_idx,
                                           decorated=_decorated)
        function(_self, _message, *args, **kwargs)

    @staticmethod
    @functools.lru_cache()
    def make_log_function(level, log_exception=False, frame_idx=1, decorated=False):

        if isinstance(level, str):
            level_id = level_name = level
        elif isinstance(level, int):
            if level < 0:
                raise ValueError("Invalid level value (%d), it should be a positive number" % level)
            level_id = None
            level_name = 'Level %d' % level
        else:
            raise ValueError("Invalid level, it should be an int or a string, not: '%s'" % type(level).__name__)

        escaping_formatter = EscapingFormatter()

        def log_function(_self, _message, *args, **kwargs):
            frame = getframe(frame_idx)
            name = frame.f_globals['__name__']

            # TODO: Early exit if no handler

            now = pendulum_now()
            now._FORMATTER = 'alternative'

            message = escaping_formatter.vformat(_message, args, kwargs)

            if level_id is None:
                level_no, level_color, level_icon = level, '', ' '
            else:
                level_no, level_color, level_icon = _self._levels[level_name]

            code = frame.f_code
            file_path = normcase(code.co_filename)
            file_name = basename(file_path)
            thread = current_thread()
            process = current_process()
            diff = now - start_time
            elapsed = pendulum.Interval(microseconds=diff.microseconds)

            level_recattr = LevelRecattr(level_name)
            level_recattr.no, level_recattr.name, level_recattr.icon = level_no, level_name, level_icon

            file_recattr = FileRecattr(file_name)
            file_recattr.name, file_recattr.path = file_name, file_path

            thread_recattr = ThreadRecattr(thread.ident)
            thread_recattr.id, thread_recattr.name = thread.ident, thread.name

            process_recattr = ProcessRecattr(process.ident)
            process_recattr.id, process_recattr.name = process.ident, process.name

            exception = None
            if log_exception:
                ex_type, ex, tb = exc_info()

                if decorated:
                    bad_frame = (tb.tb_frame.f_code.co_filename, tb.tb_frame.f_lineno)
                    tb = tb.tb_next

                root_frame = tb.tb_frame.f_back

                # TODO: Test edge cases (look in CPython source code for traceback objects and exc.__traceback__ usages)

                loguru_tracebacks = []
                while tb:
                    loguru_tb = loguru_traceback(tb.tb_frame, tb.tb_lasti, tb.tb_lineno, None)
                    loguru_tracebacks.append(loguru_tb)
                    tb = tb.tb_next

                for prev_tb, next_tb in zip(loguru_tracebacks, loguru_tracebacks[1:]):
                    prev_tb.tb_next = next_tb

                root_tb = loguru_tracebacks[0] if loguru_tracebacks else None

                frames = []
                while root_frame:
                    frames.insert(0, root_frame)
                    root_frame = root_frame.f_back

                if decorated:
                    frames = [f for f in frames if (f.f_code.co_filename, f.f_lineno) != bad_frame]
                    caught_tb = None
                else:
                    caught_tb = root_tb

                for f in reversed(frames):
                    root_tb = loguru_traceback(f, f.f_lasti, f.f_lineno, root_tb)
                    if decorated and caught_tb is None:
                        caught_tb = root_tb

                if caught_tb:
                    caught_tb.__is_caught_point__ = True

                exception = (ex_type, ex, root_tb)

            record = {
                'elapsed': elapsed,
                'extra': _self.extra,
                'file': file_recattr,
                'function': code.co_name,
                'level': level_recattr,
                'line': frame.f_lineno,
                'message': message,
                'module': splitext(file_name)[0],
                'name': name,
                'process': process_recattr,
                'thread': thread_recattr,
                'time': now,
            }

            record['message'] = record['message'].format_map(record)

            for handler in _self._handlers.values():
                handler.emit(record, exception, level_color)

        doc = "Log 'message.format(*args, **kwargs)' with severity '{}'.".format(level_name)
        if log_exception:
            doc += ' Log also current traceback.'
        log_function.__doc__ = doc

        return log_function

    trace = make_log_function.__func__("TRACE")
    debug = make_log_function.__func__("DEBUG")
    info = make_log_function.__func__("INFO")
    success = make_log_function.__func__("SUCCESS")
    warning = make_log_function.__func__("WARNING")
    error = make_log_function.__func__("ERROR")
    exception = make_log_function.__func__("ERROR", True)
    critical = make_log_function.__func__("CRITICAL")
