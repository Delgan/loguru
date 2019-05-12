import functools
import json
import multiprocessing
import sys
import threading
import traceback
from string import Formatter

from ._ansimarkup import AnsiMarkup


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
        ansi_colors=[]
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

            for ansi_code in ansi_colors:
                self.update_format(ansi_code)

        if self._enqueue:
            self._queue = multiprocessing.SimpleQueue()
            self._thread = threading.Thread(target=self._queued_writer, daemon=True)
            self._thread.start()

    def emit(self, record, level_ansi_code, is_ansi, is_raw):
        try:
            if self._levelno > record["level"].no:
                return

            if self._filter is not None:
                if not self._filter(record):
                    return

            if self._is_formatter_dynamic:
                format_ = self._formatter(record)
                if self._colorize:
                    if is_ansi:
                        precomputed_format = format_
                    else:
                        precomputed_format = self._colorize_format(format_, level_ansi_code)
                else:
                    precomputed_format = self._decolorize_format(format_)
            else:
                if self._colorize:
                    if is_ansi:
                        precomputed_format = self._static_format
                    else:
                        precomputed_format = self._precolorized_formats[level_ansi_code]
                else:
                    precomputed_format = self._decolorized_format

            formatter_record = record.copy()

            if not record["exception"]:
                formatter_record["exception"] = ""
            else:
                type_, value, tb = record["exception"]
                lines = self._exception_formatter.format_exception(type_, value, tb)
                formatter_record["exception"] = "".join(lines)

            if is_raw:
                if not is_ansi:
                    formatted = record["message"]
                elif self._colorize:
                    formatted = self._colorize_format(record["message"], level_ansi_code)
                else:
                    formatted = self._decolorize_format(record["message"])
            else:
                if not is_ansi:
                    formatted = precomputed_format.format_map(formatter_record)
                elif self._colorize:
                    formatted = self._colorize_with_tags(
                        precomputed_format, level_ansi_code, formatter_record
                    )
                else:
                    formatter_record["message"] = self._decolorize_format(record["message"])
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
            if self._catch:
                self._handle_error(record)
            else:
                raise

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
    @functools.lru_cache(maxsize=32)
    def _decolorize_format(format_):
        markups = {"level": "", "lvl": ""}
        return AnsiMarkup(custom_markups=markups, strip=True).feed(format_, strict=True)

    @staticmethod
    @functools.lru_cache(maxsize=32)
    def _colorize_format(format_, ansi_code):
        markups = {"level": ansi_code, "lvl": ansi_code}
        return AnsiMarkup(custom_markups=markups, strip=False).feed(format_, strict=True)

    @staticmethod
    def _colorize_with_tags(format_, ansi_code, record):
        markups = {"level": ansi_code, "lvl": ansi_code}
        ansimarkup = AnsiMarkup(custom_markups=markups, strip=False)

        class AnsiDict(dict):
            def __getitem__(self, key):
                if key == "message":
                    return ansimarkup.feed(record["message"], strict=True)
                return record[key]

        class AnsiFormatter(Formatter):
            def parse(self, format_string):
                for text, name, spec, conv in Formatter.parse(self, format_string):
                    text = ansimarkup.feed(text, strict=False)
                    yield (text, name, spec, conv)

        formatter = AnsiFormatter()
        dct = AnsiDict()
        return formatter.vformat(format_, (), dct)

    def _queued_writer(self):
        message = None
        queue = self._queue
        while True:
            try:
                message = queue.get()
                if message is None:
                    break
                self._writer(message)
            except Exception:
                if self._catch:
                    if message and hasattr(message, "record"):
                        message = message.record
                    self._handle_error(message)
                else:
                    raise

    def _handle_error(self, record=None):
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
