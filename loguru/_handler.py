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
        backtrace,
        catch,
        enqueue,
        encoding,
        id_,
        colors=[]
    ):
        self.writer = writer
        self.stopper = stopper
        self.levelno = levelno
        self.formatter = formatter
        self.is_formatter_dynamic = is_formatter_dynamic
        self.filter = filter_
        self.colorize = colorize
        self.serialize = serialize
        self.backtrace = backtrace
        self.catch = catch
        self.enqueue = enqueue
        self.encoding = encoding
        self.id = id_

        self.static_format = None
        self.decolorized_format = None
        self.precolorized_formats = {}

        self.lock = threading.Lock()
        self.queue = None
        self.thread = None
        self.stopped = False

        if not self.is_formatter_dynamic:
            self.static_format = self.formatter
            self.decolorized_format = self.decolorize_format(self.static_format)

            for color in colors:
                self.update_format(color)

        if self.enqueue:
            self.queue = multiprocessing.SimpleQueue()
            self.thread = threading.Thread(target=self.queued_writer, daemon=True)
            self.thread.start()

    @staticmethod
    def serialize_record(text, record):
        exc = record["exception"]
        serializable = {
            "text": text,
            "record": {
                "elapsed": dict(repr=record["elapsed"], seconds=record["elapsed"].total_seconds()),
                "exception": exc
                and dict(type=exc.type.__name__, value=exc.value, traceback=bool(exc.traceback)),
                "extra": record["extra"],
                "file": dict(name=record["file"].name, path=record["file"].path),
                "function": record["function"],
                "level": dict(
                    icon=record["level"].icon, name=record["level"].name, no=record["level"].no
                ),
                "line": record["line"],
                "message": record["message"],
                "module": record["module"],
                "name": record["name"],
                "process": dict(id=record["process"].id, name=record["process"].name),
                "thread": dict(id=record["thread"].id, name=record["thread"].name),
                "time": dict(repr=record["time"], timestamp=record["time"].timestamp()),
            },
        }

        return json.dumps(serializable, default=str) + "\n"

    @staticmethod
    def make_ansimarkup(color):
        color = ansimarkup.parse(color)
        custom_markup = dict(level=color, lvl=color)
        am = ansimarkup.AnsiMarkup(tags=custom_markup, strict=True)
        return am

    @staticmethod
    @functools.lru_cache(maxsize=32)
    def decolorize_format(format_):
        am = Handler.make_ansimarkup("")
        return am.strip(format_)

    @staticmethod
    @functools.lru_cache(maxsize=32)
    def colorize_format(format_, color):
        am = Handler.make_ansimarkup(color.strip())
        return am.parse(format_)

    def update_format(self, color):
        if self.is_formatter_dynamic or not self.colorize or color in self.precolorized_formats:
            return
        self.precolorized_formats[color] = self.colorize_format(self.static_format, color)

    def handle_error(self, record=None):
        if not self.catch:
            raise

        if not sys.stderr:
            return

        ex_type, ex, tb = sys.exc_info()

        try:
            sys.stderr.write("--- Logging error in Loguru Handler #%d ---\n" % self.id)
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

    def emit(self, record, level_color, ansi_message, raw):
        try:
            if self.levelno > record["level"].no:
                return

            if self.filter is not None:
                if not self.filter(record):
                    return

            if self.is_formatter_dynamic:
                format_ = self.formatter(record)
                if self.colorize:
                    if ansi_message:
                        precomputed_format = format_
                    else:
                        precomputed_format = self.colorize_format(format_, level_color)
                else:
                    precomputed_format = self.decolorize_format(format_)
            else:
                if self.colorize:
                    if ansi_message:
                        precomputed_format = self.static_format
                    else:
                        precomputed_format = self.precolorized_formats[level_color]
                else:
                    precomputed_format = self.decolorized_format

            exception = record["exception"]

            if exception:
                error = exception.format_exception(self.backtrace, self.colorize, self.encoding)
            else:
                error = ""

            formatter_record = {**record, **{"exception": error}}

            if ansi_message and not self.colorize:
                formatter_record["message"] = self.decolorize_format(record["message"])

            if raw:
                formatted = formatter_record["message"]
            else:
                formatted = precomputed_format.format_map(formatter_record)

            if ansi_message and self.colorize:
                try:
                    formatted = self.colorize_format(formatted, level_color)
                except ansimarkup.AnsiMarkupError:
                    formatter_record["message"] = self.decolorize_format(record["message"])

                    if self.is_formatter_dynamic:
                        precomputed_format = self.decolorize_format(format_)
                    else:
                        precomputed_format = self.decolorized_format

                    formatted = precomputed_format.format_map(formatter_record)

            if self.serialize:
                formatted = self.serialize_record(formatted, record)

            str_record = StrRecord(formatted)
            str_record.record = record

            with self.lock:
                if self.stopped:
                    return
                if self.enqueue:
                    self.queue.put(str_record)
                else:
                    self.writer(str_record)

        except Exception:
            self.handle_error(record)

    def queued_writer(self):
        message = None
        queue = self.queue
        try:
            while True:
                message = queue.get()
                if message is None:
                    break
                self.writer(message)
        except Exception:
            if message and hasattr(message, "record"):
                message = message.record
            self.handle_error(message)

    def stop(self):
        with self.lock:
            self.stopped = True
            if self.enqueue:
                self.queue.put(None)
                self.thread.join()
            self.stopper()
