import functools
import json
import multiprocessing
import string
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

        self.static_format = None
        self.decolorized_format = None
        self.precolorized_formats = {}

        self.lock = threading.Lock()
        self.queue = None
        self.thread = None

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
        am = Handler.make_ansimarkup(color)
        return am.parse(format_)

    def update_format(self, color):
        if self.is_formatter_dynamic or not self.colorize or color in self.precolorized_formats:
            return
        self.precolorized_formats[color] = self.colorize_format(self.static_format, color)

    @staticmethod
    def format_message_only(format_, message):
        formatted = ""
        formatter = string.Formatter()

        for literal_text, field_name, format_spec, conversion in formatter.parse(format_):
            if field_name is None:
                literal_text = literal_text.replace("{", "{{").replace("}", "}}")
            elif field_name == "message":
                value = formatter.convert_field(message, conversion)
                value = formatter.format_field(value, format_spec)
                literal_text += value.replace("{", "{{").replace("}", "}}")
            else:
                literal_text += "{%s" % field_name
                if conversion:
                    literal_text += "!%s" % conversion
                if format_spec:
                    literal_text += ":%s" % format_spec
                literal_text += "}"
            formatted += literal_text

        return formatted

    def handle_error(self, record=None):
        if not self.catch:
            raise

        if not sys.stderr:
            return

        ex_type, ex, tb = sys.exc_info()

        try:
            sys.stderr.write("--- Logging error in Loguru ---\n")
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

            if ansi_message:
                if self.is_formatter_dynamic:
                    format_ = self.formatter(record)
                else:
                    format_ = self.static_format

                message = record["message"]
                format_ = self.format_message_only(format_, message)

                if self.colorize:
                    precomputed_format = self.colorize_format(format_, level_color)
                    record["message"] = self.colorize_format(message, level_color)
                else:
                    precomputed_format = self.decolorize_format(format_)
                    record["message"] = self.decolorize_format(message)
            elif self.is_formatter_dynamic:
                if self.colorize:
                    precomputed_format = self.colorize_format(self.formatter(record), level_color)
                else:
                    precomputed_format = self.decolorize_format(self.formatter(record))
            else:
                if self.colorize:
                    precomputed_format = self.precolorized_formats[level_color]
                else:
                    precomputed_format = self.decolorized_format

            error = ""
            if record["exception"]:
                error = record["exception"].format_exception(
                    self.backtrace, self.colorize, self.encoding
                )
            formatter_record = {**record, **{"exception": error}}

            if raw:
                formatted = formatter_record["message"]
            else:
                formatted = precomputed_format.format_map(formatter_record)

            if self.serialize:
                formatted = self.serialize_record(formatted, record)

            str_record = StrRecord(formatted)
            str_record.record = record

            with self.lock:
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
        if self.enqueue:
            self.queue.put(None)
            self.thread.join()
        self.stopper()
