import functools
import itertools
import logging
import threading
from collections import namedtuple
from datetime import timedelta
from inspect import isclass
from multiprocessing import current_process
from os import PathLike
from os.path import basename, normcase, splitext
from threading import current_thread

from colorama import AnsiToWin32

from . import _defaults
from ._datetime import now
from ._file_sink import FileSink
from ._get_frame import get_frame
from ._handler import Handler
from ._recattrs import ExceptionRecattr, FileRecattr, LevelRecattr, ProcessRecattr, ThreadRecattr

Level = namedtuple("Level", ["no", "color", "icon"])

start_time = now()


class Logger:

    _levels = {
        "TRACE": Level(
            _defaults.LOGURU_TRACE_NO, _defaults.LOGURU_TRACE_COLOR, _defaults.LOGURU_TRACE_ICON
        ),
        "DEBUG": Level(
            _defaults.LOGURU_DEBUG_NO, _defaults.LOGURU_DEBUG_COLOR, _defaults.LOGURU_DEBUG_ICON
        ),
        "INFO": Level(
            _defaults.LOGURU_INFO_NO, _defaults.LOGURU_INFO_COLOR, _defaults.LOGURU_INFO_ICON
        ),
        "SUCCESS": Level(
            _defaults.LOGURU_SUCCESS_NO,
            _defaults.LOGURU_SUCCESS_COLOR,
            _defaults.LOGURU_SUCCESS_ICON,
        ),
        "WARNING": Level(
            _defaults.LOGURU_WARNING_NO,
            _defaults.LOGURU_WARNING_COLOR,
            _defaults.LOGURU_WARNING_ICON,
        ),
        "ERROR": Level(
            _defaults.LOGURU_ERROR_NO, _defaults.LOGURU_ERROR_COLOR, _defaults.LOGURU_ERROR_ICON
        ),
        "CRITICAL": Level(
            _defaults.LOGURU_CRITICAL_NO,
            _defaults.LOGURU_CRITICAL_COLOR,
            _defaults.LOGURU_CRITICAL_ICON,
        ),
    }

    _handlers_count = itertools.count()
    _handlers = {}

    _extra_class = {}

    _min_level = float("inf")
    _enabled = {}
    _activation_list = []

    _lock = threading.Lock()

    def __init__(self, extra, exception, record, lazy, ansi, raw, depth):
        self._extra = extra
        self._record = record
        self._exception = exception
        self._lazy = lazy
        self._ansi = ansi
        self._raw = raw
        self._depth = depth

    def start(
        self,
        sink,
        *,
        level=_defaults.LOGURU_LEVEL,
        format=_defaults.LOGURU_FORMAT,
        filter=_defaults.LOGURU_FILTER,
        colorize=_defaults.LOGURU_COLORIZE,
        serialize=_defaults.LOGURU_SERIALIZE,
        backtrace=_defaults.LOGURU_BACKTRACE,
        enqueue=_defaults.LOGURU_ENQUEUE,
        catch=_defaults.LOGURU_CATCH,
        **kwargs
    ):
        if colorize is None and serialize:
            colorize = False

        if isclass(sink):
            sink = sink(**kwargs)
            return self.start(
                sink,
                level=level,
                format=format,
                filter=filter,
                colorize=colorize,
                serialize=serialize,
                backtrace=backtrace,
                enqueue=enqueue,
                catch=catch,
            )
        elif isinstance(sink, (str, PathLike)):
            path = sink
            sink = FileSink(path, **kwargs)
            return self.start(
                sink,
                level=level,
                format=format,
                filter=filter,
                colorize=colorize,
                serialize=serialize,
                backtrace=backtrace,
                enqueue=enqueue,
                catch=catch,
            )
        elif hasattr(sink, "write") and callable(sink.write):
            try:
                converter = AnsiToWin32(sink, convert=None, strip=False)
            except Exception:
                if colorize is None:
                    colorize = False
                stream = sink
            else:
                if colorize is False or not converter.should_wrap():
                    stream = sink
                else:
                    colorize = True
                    stream = converter.stream

            stream_write = stream.write
            if kwargs:

                def write(m):
                    return stream_write(m, **kwargs)

            else:
                write = stream_write

            if hasattr(stream, "flush") and callable(stream.flush):
                stream_flush = stream.flush

                def writer(m):
                    write(m)
                    stream_flush()

            else:
                writer = write

            if hasattr(stream, "stop") and callable(stream.stop):
                stopper = stream.stop
            else:

                def stopper():
                    return None

        elif isinstance(sink, logging.Handler):

            def writer(m):
                r = m.record
                exc = r["exception"]
                record = logging.root.makeRecord(
                    r["name"],
                    r["level"].no,
                    r["file"].path,
                    r["line"],
                    r["message"],
                    (),
                    (exc.type, exc.value, exc.traceback) if exc else None,
                    r["function"],
                    r["extra"],
                )
                sink.handle(record)

            stopper = sink.close
            if colorize is None:
                colorize = False
        elif callable(sink):
            if kwargs:

                def writer(m):
                    return sink(m, **kwargs)

            else:
                writer = sink

            def stopper():
                return None

            if colorize is None:
                colorize = False
        else:
            raise ValueError("Cannot log to objects of type '%s'." % type(sink).__name__)

        if filter is None or filter == "":
            filter_func = None
        elif isinstance(filter, str):
            parent = filter + "."
            length = len(parent)

            def filter_func(r):
                return (r["name"] + ".")[:length] == parent

        elif callable(filter):
            filter_func = filter
        else:
            raise ValueError(
                "Invalid filter, it should be a function or a string, not: '%s'"
                % type(filter).__name__
            )

        if isinstance(level, str):
            levelno = self.level(level).no
        elif isinstance(level, int):
            levelno = level
        else:
            raise ValueError(
                "Invalid level, it should be an integer or a string, not: '%s'"
                % type(level).__name__
            )

        if levelno < 0:
            raise ValueError(
                "Invalid level value, it should be a positive integer, not: %d" % levelno
            )

        if isinstance(format, str):
            formatter = format + "\n{exception}"
            is_formatter_dynamic = False
        elif callable(format):
            formatter = format
            is_formatter_dynamic = True
        else:
            raise ValueError(
                "Invalid format, it should be a string or a function, not: '%s'"
                % type(format).__name__
            )

        with self._lock:
            colors = [lvl.color for lvl in self._levels.values()] + [""]

            handler = Handler(
                writer=writer,
                stopper=stopper,
                levelno=levelno,
                formatter=formatter,
                is_formatter_dynamic=is_formatter_dynamic,
                filter_=filter_func,
                colorize=colorize,
                serialize=serialize,
                backtrace=backtrace,
                catch=catch,
                enqueue=enqueue,
                colors=colors,
            )

            handler_id = next(self._handlers_count)
            self._handlers[handler_id] = handler
            self.__class__._min_level = min(self.__class__._min_level, levelno)

        return handler_id

    def stop(self, handler_id=None):
        with self._lock:
            if handler_id is None:
                for handler in self._handlers.values():
                    handler.stop()
                self._handlers.clear()
            else:
                try:
                    handler = self._handlers.pop(handler_id)
                except KeyError:
                    raise ValueError("There is no started handler with id '%s'" % handler_id)
                handler.stop()

            levelnos = (h.levelno for h in self._handlers.values())
            self.__class__._min_level = min(levelnos, default=float("inf"))

    def catch(
        self,
        exception=Exception,
        *,
        level="ERROR",
        reraise=False,
        message="An error has been caught in function '{record[function]}', "
        "process '{record[process].name}' ({record[process].id}), "
        "thread '{record[thread].name}' ({record[thread].id}):"
    ):
        if callable(exception) and (
            not isclass(exception) or not issubclass(exception, BaseException)
        ):
            return self.catch()(exception)

        class Catcher:
            def __init__(self, as_decorator):
                self._as_decorator = as_decorator

            def __enter__(self_):
                return None

            def __exit__(self_, type_, value, traceback_):
                if type_ is None:
                    return

                if not issubclass(type_, exception):
                    return False

                if self_._as_decorator:
                    back, decorator = 2, True
                else:
                    back, decorator = 1, False

                logger_ = self.opt(
                    exception=True,
                    record=True,
                    lazy=self._lazy,
                    ansi=self._ansi,
                    raw=self._raw,
                    depth=self._depth + back,
                )

                log = logger_._make_log_function(level, decorator)

                log(logger_, message)

                return not reraise

            def __call__(self_, function):
                catcher = Catcher(True)

                @functools.wraps(function)
                def catch_wrapper(*args, **kwargs):
                    with catcher:
                        return function(*args, **kwargs)

                return catch_wrapper

        return Catcher(False)

    def opt(self, *, exception=None, record=False, lazy=False, ansi=False, raw=False, depth=0):
        return Logger(self._extra, exception, record, lazy, ansi, raw, depth)

    def bind(_self, **kwargs):
        return Logger(
            {**_self._extra, **kwargs},
            _self._exception,
            _self._record,
            _self._lazy,
            _self._ansi,
            _self._raw,
            _self._depth,
        )

    def level(self, name, no=None, color=None, icon=None):
        if not isinstance(name, str):
            raise ValueError(
                "Invalid level name, it should be a string, not: '%s'" % type(name).__name__
            )

        if no is color is icon is None:
            try:
                return self._levels[name]
            except KeyError:
                raise ValueError("Level '%s' does not exist" % name)

        if name not in self._levels:
            if no is None:
                raise ValueError(
                    "Level '%s' does not exist, you have to create it by specifying a level no"
                    % name
                )
            else:
                old_no, old_color, old_icon = None, "", " "
        else:
            old_no, old_color, old_icon = self.level(name)

        if no is None:
            no = old_no

        if color is None:
            color = old_color

        if icon is None:
            icon = old_icon

        if not isinstance(no, int):
            raise ValueError(
                "Invalid level no, it should be an integer, not: '%s'" % type(no).__name__
            )

        if no < 0:
            raise ValueError("Invalid level no, it should be a positive integer, not: %d" % no)

        self._levels[name] = Level(no, color, icon)

        with self._lock:
            for handler in self._handlers.values():
                handler.update_format(color)

        return self.level(name)

    def enable(self, name):
        self._change_activation(name, True)

    def disable(self, name):
        self._change_activation(name, False)

    def configure(self, *, handlers=None, levels=None, extra=None, activation=None):
        if handlers is not None:
            self.stop()
        else:
            handlers = []

        if levels is not None:
            for params in levels:
                self.level(**params)

        if extra is not None:
            with self._lock:
                self._extra_class.clear()
                self._extra_class.update(extra)

        if activation is not None:
            for name, state in activation:
                if state:
                    self.enable(name)
                else:
                    self.disable(name)

        return [self.start(**params) for params in handlers]

    def _change_activation(self, name, status):
        if not isinstance(name, str):
            raise ValueError("Invalid name, it should be a string, not: '%s'" % type(name).__name__)

        if name != "":
            name += "."

        with self._lock:
            activation_list = [(n, s) for n, s in self._activation_list if n[: len(name)] != name]

        parent_status = next((s for n, s in activation_list if name[: len(n)] == n), None)
        if parent_status != status and not (name == "" and status == True):
            activation_list.append((name, status))

            def key_sort(x):
                return x[0].count(".")

            activation_list.sort(key=key_sort, reverse=True)

        with self._lock:
            for n in self._enabled:
                if (n + ".")[: len(name)] == name:
                    self._enabled[n] = status

            self._activation_list[:] = activation_list

    @staticmethod
    @functools.lru_cache()
    def _make_log_function(level, decorated=False):

        if isinstance(level, str):
            level_id = level_name = level
        elif isinstance(level, int):
            if level < 0:
                raise ValueError(
                    "Invalid level value, it should be a positive integer, not: %d" % level
                )
            level_id = None
            level_name = "Level %d" % level
        else:
            raise ValueError(
                "Invalid level, it should be an integer or a string, not: '%s'"
                % type(level).__name__
            )

        def log_function(_self, _message, *args, **kwargs):
            if not _self._handlers:
                return

            frame = get_frame(_self._depth + 1)
            name = frame.f_globals["__name__"]

            try:
                if not _self._enabled[name]:
                    return
            except KeyError:
                dotted_name = name + "."
                for dotted_module_name, status in _self._activation_list:
                    if dotted_name[: len(dotted_module_name)] == dotted_module_name:
                        if status:
                            break
                        _self._enabled[name] = False
                        return
                _self._enabled[name] = True

            current_datetime = now()

            if level_id is None:
                level_no, level_color, level_icon = level, "", " "
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
            diff = current_datetime - start_time
            elapsed = timedelta(microseconds=diff.microseconds)

            level_recattr = LevelRecattr(level_name)
            level_recattr.no, level_recattr.name, level_recattr.icon = (
                level_no,
                level_name,
                level_icon,
            )

            file_recattr = FileRecattr(file_name)
            file_recattr.name, file_recattr.path = file_name, file_path

            thread_recattr = ThreadRecattr(thread.ident)
            thread_recattr.id, thread_recattr.name = thread.ident, thread.name

            process_recattr = ProcessRecattr(process.ident)
            process_recattr.id, process_recattr.name = process.ident, process.name

            if _self._exception:
                exception = ExceptionRecattr(_self._exception, decorated)
            else:
                exception = None

            record = {
                "elapsed": elapsed,
                "exception": exception,
                "extra": {**_self._extra_class, **_self._extra},
                "file": file_recattr,
                "function": code.co_name,
                "level": level_recattr,
                "line": frame.f_lineno,
                "message": _message,
                "module": splitext(file_name)[0],
                "name": name,
                "process": process_recattr,
                "thread": thread_recattr,
                "time": current_datetime,
            }

            if _self._lazy:
                args = [arg() for arg in args]
                kwargs = {key: value() for key, value in kwargs.items()}

            if _self._record:
                record["message"] = _message.format(*args, **kwargs, record=record)
            elif args or kwargs:
                record["message"] = _message.format(*args, **kwargs)

            for handler in _self._handlers.values():
                handler.emit(record, level_color, _self._ansi, _self._raw)

        doc = "Log 'message.format(*args, **kwargs)' with severity '%s'." % level_name
        log_function.__doc__ = doc

        return log_function

    trace = _make_log_function.__func__("TRACE")
    debug = _make_log_function.__func__("DEBUG")
    info = _make_log_function.__func__("INFO")
    success = _make_log_function.__func__("SUCCESS")
    warning = _make_log_function.__func__("WARNING")
    error = _make_log_function.__func__("ERROR")
    critical = _make_log_function.__func__("CRITICAL")

    def log(_self, _level, _message, *args, **kwargs):
        """Log 'message.format(*args, **kwargs)' with severity _level."""
        logger = _self.opt(
            exception=_self._exception,
            record=_self._record,
            lazy=_self._lazy,
            ansi=_self._ansi,
            raw=_self._raw,
            depth=_self._depth + 1,
        )
        logger._make_log_function(_level)(logger, _message, *args, **kwargs)

    def exception(_self, _message, *args, **kwargs):
        """Convenience method for logging an 'ERROR' with exception information."""
        logger = _self.opt(
            exception=True,
            record=_self._record,
            lazy=_self._lazy,
            ansi=_self._ansi,
            raw=_self._raw,
            depth=_self._depth + 1,
        )
        logger._make_log_function("ERROR")(logger, _message, *args, **kwargs)
