import functools
import json
import multiprocessing
import sys
import threading
import traceback

import ansimarkup


class StrRecord(str):
    __slots__ = ("record",)


class Handler:
    def __init__(
        self,
        *,
        writer,
        stopper,
        levelno,
        formatter,
        is_formatter_dynamic,
        filter_,
        colorize,
        serialize,
        catch,
        enqueue,
        exception_formatter,
        id_,
        colors=[]
    ):
        self._writer = writer
        self._stopper = stopper
        self._levelno = levelno
        self._formatter = formatter
        self._is_formatter_dynamic = is_formatter_dynamic
        self._filter = filter_
        self._colorize = colorize
        self._serialize = serialize
        self._catch = catch
        self._enqueue = enqueue
        self._exception_formatter = exception_formatter
        self._id = id_

        self._static_format = None
        self._decolorized_format = None
        self._precolorized_formats = {}

        self._lock = threading.Lock()
        self._queue = None
        self._thread = None
        self._stopped = False

        if not self._is_formatter_dynamic:
            self._static_format = self._formatter
            self._decolorized_format = self._decolorize_format(self._static_format)

            for color in colors:
                self.update_format(color)

        if self._enqueue:
            self._queue = multiprocessing.SimpleQueue()
            self._thread = threading.Thread(target=self._queued_writer, daemon=True)
            self._thread.start()

    def emit(self, record, level_color, ansi_message, raw):
        try:
            if self._levelno > record["level"].no:
                return

            if self._filter is not None:
                if not self._filter(record):
                    return

            if self._is_formatter_dynamic:
                format_ = self._formatter(record)
                if self._colorize:
                    if ansi_message:
                        precomputed_format = format_
                    else:
                        precomputed_format = self._colorize_format(format_, level_color)
                else:
                    precomputed_format = self._decolorize_format(format_)
            else:
                if self._colorize:
                    if ansi_message:
                        precomputed_format = self._static_format
                    else:
                        precomputed_format = self._precolorized_formats[level_color]
                else:
                    precomputed_format = self._decolorized_format

            formatter_record = record.copy()

            if not record["exception"]:
                error = ""
            else:
                type_, value, tb = record["exception"]
                lines = self._exception_formatter.format_exception(type_, value, tb)
                error = "".join(lines)

            formatter_record["exception"] = error

            if ansi_message and not self._colorize:
                formatter_record["message"] = self._decolorize_format(record["message"])

            if raw:
                formatted = formatter_record["message"]
            else:
                formatted = precomputed_format.format_map(formatter_record)

            if ansi_message and self._colorize:
                try:
                    formatted = self._colorize_format(formatted, level_color)
                except ansimarkup.AnsiMarkupError:
                    formatter_record["message"] = self._decolorize_format(record["message"])

                    if self._is_formatter_dynamic:
                        precomputed_format = self._decolorize_format(format_)
                    else:
                        precomputed_format = self._decolorized_format

                    formatted = precomputed_format.format_map(formatter_record)

            if self._serialize:
                formatted = self._serialize_record(formatted, record)

            str_record = StrRecord(formatted)
            str_record.record = record

            with self._lock:
                if self._stopped:
                    return
                if self._enqueue:
                    self._queue.put(str_record)
                else:
                    self._writer(str_record)

        except Exception:
            self._handle_error(record)

    def stop(self):
        with self._lock:
            self._stopped = True
            if self._enqueue:
                self._queue.put(None)
                self._thread.join()
            self._stopper()

    def update_format(self, color):
        if self._is_formatter_dynamic or not self._colorize or color in self._precolorized_formats:
            return
        self._precolorized_formats[color] = self._colorize_format(self._static_format, color)

    @property
    def levelno(self):
        return self._levelno

    @staticmethod
    def _serialize_record(text, record):
        serializable = {
            "text": text,
            "record": {
                "elapsed": {
                    "repr": record["elapsed"],
                    "seconds": record["elapsed"].total_seconds(),
                },
                "exception": record["exception"]
                and {
                    "type": record["exception"].type.__name__,
                    "value": record["exception"].value,
                    "traceback": bool(record["exception"].traceback),
                },
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

        return json.dumps(serializable, default=str) + "\n"

    @staticmethod
    def _make_ansimarkup(color):
        color = ansimarkup.parse(color)
        custom_markup = dict(level=color, lvl=color)
        am = ansimarkup.AnsiMarkup(tags=custom_markup, strict=True)
        return am

    @staticmethod
    @functools.lru_cache(maxsize=32)
    def _decolorize_format(format_):
        am = Handler._make_ansimarkup("")
        return am.strip(format_)

    @staticmethod
    @functools.lru_cache(maxsize=32)
    def _colorize_format(format_, color):
        am = Handler._make_ansimarkup(color.strip())
        return am.parse(format_)

    def _handle_error(self, record=None):
        if not self._catch:
            raise

        if not sys.stderr:
            return

        ex_type, ex, tb = sys.exc_info()

        try:
            sys.stderr.write("--- Logging error in Loguru Handler #%d ---\n" % self._id)
            sys.stderr.write("Record was: ")
            try:
                sys.stderr.write(str(record))
            except Exception:
                sys.stderr.write("/!\\ Unprintable record /!\\")
            sys.stderr.write("\n")
            traceback.print_exception(ex_type, ex, tb, None, sys.stderr)
            sys.stderr.write("--- End of logging error ---\n")
        except OSError:
            pass
        finally:
            del ex_type, ex, tb

    def _queued_writer(self):
        message = None
        queue = self._queue
        try:
            while True:
                message = queue.get()
                if message is None:
                    break
                self._writer(message)
        except Exception:
            if message and hasattr(message, "record"):
                message = message.record
            self._handle_error(message)
