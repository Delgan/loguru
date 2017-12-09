import functools
import itertools
from collections import namedtuple
from inspect import isclass
from multiprocessing import current_process
from os import PathLike
from os.path import basename, normcase, splitext
from sys import exc_info
from threading import current_thread, Lock

import pendulum
from pendulum import now as pendulum_now

from . import _constants
from ._catcher import Catcher
from ._file_sink import FileSink
from ._getframe import getframe
from ._handler import Handler

Level = namedtuple('Level', ['no', 'color', 'icon'])

start_time = pendulum_now()


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

class Logger:

    _levels = {
        "TRACE": Level(_constants.LOGURU_TRACE_NO, _constants.LOGURU_TRACE_COLOR, _constants.LOGURU_TRACE_ICON),
        "DEBUG": Level(_constants.LOGURU_DEBUG_NO, _constants.LOGURU_DEBUG_COLOR, _constants.LOGURU_DEBUG_ICON),
        "INFO": Level(_constants.LOGURU_INFO_NO, _constants.LOGURU_INFO_COLOR, _constants.LOGURU_INFO_ICON),
        "SUCCESS": Level(_constants.LOGURU_SUCCESS_NO, _constants.LOGURU_SUCCESS_COLOR, _constants.LOGURU_SUCCESS_ICON),
        "WARNING": Level(_constants.LOGURU_WARNING_NO, _constants.LOGURU_WARNING_COLOR, _constants.LOGURU_WARNING_ICON),
        "ERROR": Level(_constants.LOGURU_ERROR_NO, _constants.LOGURU_ERROR_COLOR, _constants.LOGURU_ERROR_ICON),
        "CRITICAL": Level(_constants.LOGURU_CRITICAL_NO, _constants.LOGURU_CRITICAL_COLOR, _constants.LOGURU_CRITICAL_ICON),
    }

    _handlers_count = itertools.count()
    _handlers = {}

    _min_level = float("inf")
    _enabled = {}
    _activation_list = []

    _lock = Lock()

    def __init__(self, *, extra={}, record=False, exception=None, lazy=False):
        self.catch = Catcher(self)
        self.extra = extra
        self._record = record
        self._exception = exception
        self._lazy = lazy

    def opt(self, exception=None, record=None, lazy=None):
        extra = self.extra.copy()
        exception = self._exception if exception is None else exception
        record = self._record if record is None else record
        lazy = self._lazy if lazy is None else lazy
        logger = Logger(extra=extra, exception=exception, record=record, lazy=lazy)
        return logger

    def bind(self, **kwargs):
        extra = {**self.extra, **kwargs}
        logger = Logger(extra=extra, record=self._record, exception=self._exception, lazy=self._lazy)
        return logger

    def level(self, name, no=None, color=None, icon=None):
        if not isinstance(name, str):
            raise ValueError("Invalid level name, it should be a string, not: '%s'" % type(name).__name__)

        if no is color is icon is None:
            try:
                return self._levels[name]
            except KeyError:
                raise ValueError("Level '%s' does not exist" % name)

        if name not in self._levels:
            if no is None:
                raise ValueError("Level '%s' does not exist, you have to create it by specifying a level no" % name)
            else:
                old_no, old_color, old_icon = None, '', ' '
        else:
            old_no, old_color, old_icon = self.level(name)

        if no is None:
            no = old_no

        if color is None:
            color = old_color

        if icon is None:
            icon = old_icon

        if not isinstance(no, int):
            raise ValueError("Invalid level no, it should be an integer, not: '%s'" % type(no).__name__)

        if no < 0:
            raise ValueError("Invalid level no, it should be a positive integer, not: %d" % no)

        self._levels[name] = Level(no, color, icon)

        with self._lock:
            for handler in self._handlers.values():
                handler.update_format(color)

        return self.level(name)

    def configure(self, config):
        with self._lock:
            self.extra.update(config.get('extra', {}))
        for params in config.get('levels', []):
            self.level(**params)
        handlers_ids = [self.start(**params) for params in config.get('sinks', [])]
        return handlers_ids

    def _change_activation(self, name, status):
        if not isinstance(name, str):
            raise ValueError("Invalid name, it should be a string, not: '%s'" % type(name).__name__)

        if name != '':
            name += '.'

        with self._lock:
            activation_list = [(n, s) for n, s in self._activation_list if n[:len(name)] != name]

        parent_status = next((s for n, s in activation_list if name[:len(n)] == n), None)
        if parent_status != status and not (name == '' and status == True):
            activation_list.append((name, status))
            activation_list.sort(key=lambda x: x[0].count('.'), reverse=True)

        with self._lock:
            for n in self._enabled:
                if (n + '.')[:len(name)] == name:
                    self._enabled[n] = status

            self._activation_list[:] = activation_list

    def enable(self, name):
        self._change_activation(name, True)

    def disable(self, name):
        self._change_activation(name, False)

    def start(self, sink, *, level=_constants.LOGURU_LEVEL, format=_constants.LOGURU_FORMAT, filter=None,
                    colored=_constants.LOGURU_COLORED, structured=_constants.LOGURU_STRUCTURED,
                    enhanced=_constants.LOGURU_ENHANCED, guarded=_constants.LOGURU_GUARDED,
                    wrapped=_constants.LOGURU_WRAPPED, **kwargs):
        if colored is None and structured:
            colored = False

        if isclass(sink):
            sink = sink(**kwargs)
            return self.start(sink, level=level, format=format, filter=filter, colored=colored,
                              structured=structured, enhanced=enhanced, guarded=guarded,
                              wrapped=wrapped)
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
            return self.start(sink, level=level, format=format, filter=filter, colored=colored,
                              structured=structured, enhanced=enhanced, guarded=guarded,
                              wrapped=wrapped)
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

        if filter is None or filter == '':
            filter_func = None
        elif isinstance(filter, str):
            parent = filter + '.'
            length = len(parent)
            def filter_func(r):
                return (r['name'] + '.')[:length] == parent
        elif callable(filter):
            filter_func = filter
        else:
            raise ValueError("Invalid filter, it should be a function or a string, not: '%s'" % type(filter).__name__)

        if isinstance(level, str):
            levelno = self.level(level).no
        elif isinstance(level, int):
            levelno = level
        else:
            raise ValueError("Invalid level, it should be an integer or a string, not: '%s'" % type(level).__name__)

        if levelno < 0:
            raise ValueError("Invalid level value, it should be a positive integer, not: %d" % levelno)

        if not isinstance(format, str):
            raise ValueError("Invalid format, it should be a string, not: '%s'" % type(format).__name__)

        with self._lock:
            colors = [lvl.color for lvl in self._levels.values()] + ['']

            handler = Handler(
                writer=writer,
                stopper=stopper,
                levelno=levelno,
                format_=format,
                filter_=filter_func,
                colored=colored,
                structured=structured,
                enhanced=enhanced,
                guarded=guarded,
                wrapped=wrapped,
                colors=colors,
            )

            handlers_count = next(self._handlers_count)
            self._handlers[handlers_count] = handler
            self.__class__._min_level = min(self.__class__._min_level, levelno)

        return handlers_count

    def stop(self, handler_id=None):
        with self._lock:
            if handler_id is None:
                for handler in self._handlers.values():
                    handler.stop()
                self._handlers.clear()
                self.__class__._min_level = float("inf")
            elif handler_id in self._handlers:
                handler = self._handlers.pop(handler_id)
                handler.stop()
                levelnos = (h.levelno for h in self._handlers.values())
                self.__class__._min_level = min(levelnos, default=float("inf"))
            else:
                raise ValueError("There is no started handler with id '%s'" % handler_id)

    def log(_self, _level, _message, *args, **kwargs):
        _self._make_log_function(_level, False, 2, False)(_self, _message, *args, **kwargs)

    @staticmethod
    @functools.lru_cache()
    def _make_log_function(level, log_exception=False, frame_idx=1, decorated=False):

        if isinstance(level, str):
            level_id = level_name = level
        elif isinstance(level, int):
            if level < 0:
                raise ValueError("Invalid level value, it should be a positive integer, not: %d" % level)
            level_id = None
            level_name = 'Level %d' % level
        else:
            raise ValueError("Invalid level, it should be an integer or a string, not: '%s'" % type(level).__name__)

        def log_function(_self, _message, *args, **kwargs):
            if not _self._handlers:
                return

            frame = getframe(frame_idx)
            name = frame.f_globals['__name__']

            try:
                if not _self._enabled[name]:
                    return
            except KeyError:
                dotted_name = name + '.'
                for dotted_module_name, status in _self._activation_list:
                    if dotted_name[:len(dotted_module_name)] == dotted_module_name:
                        if status:
                            break
                        _self._enabled[name] = False
                        return
                _self._enabled[name] = True

            now = pendulum_now()
            now._FORMATTER = 'alternative'

            if level_id is None:
                level_no, level_color, level_icon = level, '', ' '
            else:
                try:
                    level_no, level_color, level_icon = _self._levels[level_name]
                except KeyError:
                    raise ValueError("Level '%s' does not exist" % level_name)

            if level_no < _self._min_level:
                return

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

            exception = log_exception or _self._exception
            if exception:
                if isinstance(exception, BaseException):
                    ex_type, ex, tb = (type(exception), exception, exception.__traceback__)
                elif isinstance(exception, tuple):
                    ex_type, ex, tb = exception
                else:
                    ex_type, ex, tb = exc_info()

                exception = _self._extend_exception(ex_type, ex, tb, decorated)

            record = {
                'elapsed': elapsed,
                'extra': _self.extra,
                'file': file_recattr,
                'function': code.co_name,
                'level': level_recattr,
                'line': frame.f_lineno,
                'message': _message,
                'module': splitext(file_name)[0],
                'name': name,
                'process': process_recattr,
                'thread': thread_recattr,
                'time': now,
            }

            if _self._lazy:
                args = [arg() for arg in args]
                kwargs = {key: value() for key, value in kwargs.items()}

            if _self._record:
                record['message'] = _message.format(*args, **kwargs, record=record)
            elif args or kwargs:
                record['message'] = _message.format(*args, **kwargs)

            for handler in _self._handlers.values():
                handler.emit(record, exception, level_color)

        if not log_exception:
            doc = "Log 'message.format(*args, **kwargs)' with severity '%s'." % level_name
        else:
            doc = "Convenience method for logging an '%s' with exception information." % level_name

        log_function.__doc__ = doc

        return log_function

    def handle(self, record, exception=None):
        try:
            _, level_color, _ = self._levels[record['level'].name]
        except KeyError:
            level_color = ''

        if exception:
            exception = self._extend_exception(*exception, False)

        for handler in self._handlers.values():
            handler.emit(record, exception, level_color)

    @staticmethod
    def _extend_exception(ex_type, ex, tb, decorated):
        if tb:
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

        return (ex_type, ex, tb)

    trace = _make_log_function.__func__("TRACE")
    debug = _make_log_function.__func__("DEBUG")
    info = _make_log_function.__func__("INFO")
    success = _make_log_function.__func__("SUCCESS")
    warning = _make_log_function.__func__("WARNING")
    error = _make_log_function.__func__("ERROR")
    exception = _make_log_function.__func__("ERROR", True)
    critical = _make_log_function.__func__("CRITICAL")
