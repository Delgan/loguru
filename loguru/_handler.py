import functools
import json
import multiprocessing
import os
import threading
from contextlib import contextmanager
from threading import Thread

from ._colorizer import Colorizer
from ._locks_machinery import create_handler_lock
from ._record_queue import RecordQueue


def prepare_colored_format(format_, ansi_level):
    colored = Colorizer.prepare_format(format_)
    return colored, colored.colorize(ansi_level)


def prepare_stripped_format(format_):
    colored = Colorizer.prepare_format(format_)
    return colored.strip()


def memoize(function):
    return functools.lru_cache(maxsize=64)(function)


class Message(str):
    __slots__ = ("record",)


class Handler:
    def __init__(
        self,
        *,
        sink,
        name,
        levelno,
        formatter,
        is_formatter_dynamic,
        filter_,
        colorize,
        serialize,
        enqueue,
        multiprocessing_context,
        error_interceptor,
        exception_formatter,
        id_
    ):
        self._name = name
        self._sink = sink
        self._levelno = levelno
        self._formatter = formatter
        self._is_formatter_dynamic = is_formatter_dynamic
        self._filter = filter_
        self._colorize = colorize
        self._serialize = serialize
        self._enqueue = enqueue
        self._multiprocessing_context = multiprocessing_context
        self._error_interceptor = error_interceptor
        self._exception_formatter = exception_formatter
        self._id = id_
        self._levels_ansi_codes = {}

        self._decolorized_format = None
        self._precolorized_formats = {}
        self._memoize_dynamic_format = None

        self._stopped = False
        self._lock = create_handler_lock()
        self._thread_locals = threading.local()
        self._queue = None
        self._queue_lock = None
        self._confirmation_event = None
        self._confirmation_lock = None
        self._owner_process_pid = None
        self._writer_thread = None

        # We can't use "object()" because their identity doesn't survive pickling.
        self._confirmation_sentinel = True
        self._stop_sentinel = None

        if self._is_formatter_dynamic:
            if self._colorize:
                self._memoize_dynamic_format = memoize(prepare_colored_format)
            else:
                self._memoize_dynamic_format = memoize(prepare_stripped_format)
        elif not self._colorize:
            self._decolorized_format = self._formatter.strip()

        if self._enqueue:
            if self._multiprocessing_context is None:
                self._queue = RecordQueue(
                    self._multiprocessing_context, self._error_interceptor, self._id
                )
                self._confirmation_event = multiprocessing.Event()
                self._confirmation_lock = multiprocessing.Lock()
            else:
                self._queue = RecordQueue(
                    self._multiprocessing_context, self._error_interceptor, self._id
                )
                self._confirmation_event = self._multiprocessing_context.Event()
                self._confirmation_lock = self._multiprocessing_context.Lock()
            self._queue_lock = create_handler_lock()
            self._owner_process_pid = os.getpid()
            self._writer_thread = Thread(
                target=self._threaded_writer, daemon=True, name="loguru-writer-%d" % self._id
            )
            self._writer_thread.start()

    def __repr__(self):
        return "(id=%d, level=%d, sink=%s)" % (self._id, self._levelno, self._name)

    @contextmanager
    def _protected_lock(self):
        """Acquire the lock, but fail fast if its already acquired by the current thread."""
        if getattr(self._thread_locals, "lock_acquired", False):
            raise RuntimeError(
                "Could not acquire internal lock because it was already in use (deadlock avoided). "
                "This likely happened because the logger was re-used inside a sink, a signal "
                "handler or a '__del__' method. This is not permitted because the logger and its "
                "handlers are not re-entrant."
            )
        self._thread_locals.lock_acquired = True
        try:
            with self._lock:
                yield
        finally:
            self._thread_locals.lock_acquired = False

    def emit(self, record, level_id, from_decorator, is_raw, colored_message):
        try:
            if self._levelno > record["level"].no:
                return

            if self._filter is not None:
                if not self._filter(record):
                    return

            if self._is_formatter_dynamic:
                dynamic_format = self._formatter(record)

            formatter_record = record.copy()

            if not record["exception"]:
                formatter_record["exception"] = ""
            else:
                type_, value, tb = record["exception"]
                formatter = self._exception_formatter
                lines = formatter.format_exception(type_, value, tb, from_decorator=from_decorator)
                formatter_record["exception"] = "".join(lines)

            if colored_message is not None and colored_message.stripped != record["message"]:
                colored_message = None

            if is_raw:
                if colored_message is None or not self._colorize:
                    formatted = record["message"]
                else:
                    ansi_level = self._levels_ansi_codes[level_id]
                    formatted = colored_message.colorize(ansi_level)
            elif self._is_formatter_dynamic:
                if not self._colorize:
                    precomputed_format = self._memoize_dynamic_format(dynamic_format)
                    formatted = precomputed_format.format_map(formatter_record)
                elif colored_message is None:
                    ansi_level = self._levels_ansi_codes[level_id]
                    _, precomputed_format = self._memoize_dynamic_format(dynamic_format, ansi_level)
                    formatted = precomputed_format.format_map(formatter_record)
                else:
                    ansi_level = self._levels_ansi_codes[level_id]
                    formatter, precomputed_format = self._memoize_dynamic_format(
                        dynamic_format, ansi_level
                    )
                    coloring_message = formatter.make_coloring_message(
                        record["message"], ansi_level=ansi_level, colored_message=colored_message
                    )
                    formatter_record["message"] = coloring_message
                    formatted = precomputed_format.format_map(formatter_record)

            else:
                if not self._colorize:
                    precomputed_format = self._decolorized_format
                    formatted = precomputed_format.format_map(formatter_record)
                elif colored_message is None:
                    ansi_level = self._levels_ansi_codes[level_id]
                    precomputed_format = self._precolorized_formats[level_id]
                    formatted = precomputed_format.format_map(formatter_record)
                else:
                    ansi_level = self._levels_ansi_codes[level_id]
                    precomputed_format = self._precolorized_formats[level_id]
                    coloring_message = self._formatter.make_coloring_message(
                        record["message"], ansi_level=ansi_level, colored_message=colored_message
                    )
                    formatter_record["message"] = coloring_message
                    formatted = precomputed_format.format_map(formatter_record)

            if self._serialize:
                formatted = self._serialize_record(formatted, record)

            str_record = Message(formatted)
            str_record.record = record

            with self._protected_lock():
                if self._stopped:
                    return
                if self._enqueue:
                    self._queue.put(str_record)
                else:
                    self._sink.write(str_record)
        except Exception:
            if not self._error_interceptor.should_catch():
                raise
            self._error_interceptor.print(record)

    def stop(self):
        with self._protected_lock():
            self._stopped = True
            if self._enqueue:
                if self._owner_process_pid != os.getpid():
                    self._queue.stop()
                    return
                # Although we're not waiting for any confirmation, we still need to acquire
                # the underlying Lock to ensure that not two processes try to stop and complete
                # the queue at the same time (would possibly cause deadlock).
                with self._confirmation_lock:
                    self._queue.put_final(self._stop_sentinel)
                    self._writer_thread.join()
                    self._queue.stop()
                    self._queue.close()

            self._sink.stop()

    def complete_queue(self):
        if not self._enqueue:
            return

        with self._confirmation_lock:
            if self._queue.is_closed():
                return
            with self._protected_lock():
                self._queue.put(self._confirmation_sentinel)
            self._confirmation_event.wait()
            self._confirmation_event.clear()

    def tasks_to_complete(self):
        if self._enqueue and self._owner_process_pid != os.getpid():
            return []
        lock = self._queue_lock if self._enqueue else self._protected_lock()
        with lock:
            return self._sink.tasks_to_complete()

    def update_format(self, level_id, ansi_code):
        with self._protected_lock():
            self._levels_ansi_codes[level_id] = ansi_code
            if self._colorize and not self._is_formatter_dynamic:
                self._precolorized_formats[level_id] = self._formatter.colorize(ansi_code)

    @property
    def levelno(self):
        return self._levelno

    @staticmethod
    def _serialize_record(text, record):
        exception = record["exception"]

        if exception is not None:
            exception = {
                "type": None if exception.type is None else exception.type.__name__,
                "value": exception.value,
                "traceback": bool(exception.traceback),
            }

        serializable = {
            "text": text,
            "record": {
                "elapsed": {
                    "repr": record["elapsed"],
                    "seconds": record["elapsed"].total_seconds(),
                },
                "exception": exception,
                "extra": record["extra"],
                "file": {"name": record["file"].name, "path": record["file"].path},
                "function": record["function"],
                "level": {
                    "icon": record["level"].icon,
                    "name": record["level"].name,
                    "no": record["level"].no,
                },
                "line": record["line"],
                "message": record["message"],
                "module": record["module"],
                "name": record["name"],
                "process": {"id": record["process"].id, "name": record["process"].name},
                "thread": {"id": record["thread"].id, "name": record["thread"].name},
                "time": {"repr": record["time"], "timestamp": record["time"].timestamp()},
            },
        }

        return json.dumps(serializable, default=str, ensure_ascii=False) + "\n"

    def _threaded_writer(self):
        while True:
            try:
                message = self._queue.get()
            except Exception:
                with self._queue_lock:
                    self._error_interceptor.print(None)
                continue

            if message is self._stop_sentinel:
                break

            if message is self._confirmation_sentinel:
                self._confirmation_event.set()
                continue

            try:
                # We need to use a registered Lock to protect sink during fork. In particular, if
                # this thread is writing to stderr while the main thread is forked, the lock
                # internally used by stderr might be copied while being in locked state. That would
                # cause a deadlock in the child process.
                with self._queue_lock:
                    self._sink.write(message)
            except Exception:
                self._error_interceptor.print(message.record)

    def __getstate__(self):
        state = self.__dict__.copy()
        state["_lock"] = None
        state["_thread_locals"] = None
        state["_memoize_dynamic_format"] = None
        if self._enqueue:
            state["_sink"] = None
            state["_writer_thread"] = None
            state["_owner_process"] = None
            state["_queue_lock"] = None
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self._lock = create_handler_lock()
        self._thread_locals = threading.local()
        if self._is_formatter_dynamic:
            if self._colorize:
                self._memoize_dynamic_format = memoize(prepare_colored_format)
            else:
                self._memoize_dynamic_format = memoize(prepare_stripped_format)
