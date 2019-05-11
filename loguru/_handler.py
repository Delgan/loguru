import functools
import json
import multiprocessing
import string
import sys
import threading
import traceback

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

            if raw:
                message = record["message"]
                if not ansi_message:
                    formatted = message
                elif self._colorize:
                    formatted = self._colorize_format(message, level_color)
                else:
                    formatted = self._decolorize_format(message)
            else:
                if not ansi_message:
                    formatted = precomputed_format.format_map(formatter_record)
                else:
                    formatted = self._format_with_ansi(
                        precomputed_format,
                        level_color,
                        not self._colorize,
                        record["message"],
                        formatter_record,
                    )

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
        return AnsiMarkup.strip(format_, tags={"level", "lvl"})

    @staticmethod
    @functools.lru_cache(maxsize=32)
    def _colorize_format(format_, color):
        tag = color.strip().strip("<>")
        ansi = AnsiMarkup.get_ansicode(tag) or ""
        user_tags = dict(level=ansi, lvl=ansi)
        return AnsiMarkup.parse(format_, tags=user_tags, strict=True)

    @staticmethod
    def _format_with_ansi(format_, color, strip, message, record):
        tag = color.strip().strip("<>")
        ansi = AnsiMarkup.get_ansicode(tag) or ""
        user_tags = dict(level=ansi, lvl=ansi)
        ansimarkup = AnsiMarkup(tags=user_tags, strip=strip)

        class MagicDict(dict):
            def __getitem__(self, key):
                if key == "message":
                    return ansimarkup.feed(message, strict=True)
                return record[key]

        class F(string.Formatter):
            def parse(self, format_string):
                for literal_text, field_name, format_spec, conversion in super().parse(
                    format_string
                ):
                    if not strip:
                        literal_text = ansimarkup.feed(literal_text)
                    yield (literal_text, field_name, format_spec, conversion)

        formatter = F()
        m = MagicDict()
        return formatter.vformat(format_, (), m)

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
