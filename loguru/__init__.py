import logging
import datetime
from inspect import isclass
from logging import getLevelName, addLevelName
from os import getpid, PathLike
from os.path import normcase, basename, splitext
import sys
from sys import exc_info, stdout as STDOUT, stderr as STDERR
from multiprocessing import current_process
from threading import current_thread
from traceback import format_exception
from numbers import Number
import re
import os
import glob
from collections import defaultdict, OrderedDict
from string import Formatter
import math
import functools

import ansimarkup
from better_exceptions_fork import ExceptionFormatter
from pendulum import now
import pendulum


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

def patch_datetime(date):
    date._FORMATTER = 'alternative'

def patch_datetime_file(date):
    date._FORMATTER = 'alternative'
    date._to_string_format = '%Y-%m-%d_%H-%M-%S'

class StrRecord(str):
    pass

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

    def emit(self, record):
        level = record['level']
        if self.level > level.no:
            return

        if self.filter is not None:
            if not self.filter(record):
                return

        exception = record['exception']

        formatted = self.formats_per_level[level.name].format_map(record) + '\n'
        if exception:
            if self.better_exceptions:
                formatted += ''.join(self.exception_formatter.format_exception(*exception))
            else:
                formatted += ''.join(format_exception(*exception))

        message = StrRecord(formatted)
        message.record = record

        self.writter(message)

class LevelRecattr(str):
    __slots__ = ('no', 'name')


class FileRecattr(str):
    __slots__ = ('name', 'path')


class ThreadRecattr(str):
    __slots__ = ('id', 'name')


class ProcessRecattr(str):
    __slots__ = ('id', 'name')


class FileSink:

    def __init__(self, path, *, size=None, when=None, backups=math.inf, **kwargs):
        kwargs.setdefault('mode', 'a')
        kwargs.setdefault('buffering', 1)
        self.path = str(path)
        self.kwargs = kwargs
        self.backups = self.parse_backups(backups)
        self.file = None
        self.size_based_rollover = size is not None
        self.when_based_rollover = when is not None
        self.rotating = self.size_based_rollover or self.when_based_rollover
        self.created = 0
        self.start_time = now()
        patch_datetime_file(self.start_time)

        self.rollover_size = None
        self.rollover_day = None
        self.rollover_time = None
        self.rollover_interval = None
        self.rollover_at = None

        self.regex_file_name = self.make_regex_file_name(os.path.basename(path))

        self.rollover()

        if not self.rotating:
            self.write = self.file.write
            return

        self.write = self.rotating_write

        if self.size_based_rollover:
            if callable(size):
                self.should_rollover_size = size
            else:
                self.rollover_size = self.parse_size(size)

        if self.when_based_rollover:
            if callable(when):
                self.next_rollover_time = when
            else:
                self.rollover_day, self.rollover_time, self.rollover_interval = self.parse_when(when)

            self.rollover_at = self.next_rollover_time(None, self.start_time)
            patch_datetime_file(self.rollover_at)

    def stop(self):
        if self.file is not None:
            self.file.close()
            self.file = None

    def format_path(self):
        now_ = now()
        patch_datetime_file(now_)

        info = {
            "time": now_,
            "start_time": self.start_time,
            "rotation_time": self.rollover_at,
            "n": self.created,
            "n+1": self.created + 1,
        }

        return self.path.format_map(info)

    @staticmethod
    def make_regex_file_name(file_name):
        tokens = Formatter().parse(file_name)
        regex_name = ''.join(re.escape(t[0]) + '.*' * (t[1] is not None) for t in tokens)
        regex_name += '(?:\.\d+)?'
        return re.compile(regex_name)

    @staticmethod
    def parse_backups(backups):
        if isinstance(backups, (int, datetime.timedelta)) or backups == math.inf:
            pass
        elif isinstance(backups, str):
            backups_ = backups.strip()
            if all(c.isalpha() for c in backups_):
                backups_ = '1 ' + backups_
            seconds = FileSink.parse_duration(backups_)
            if seconds is None:
                raise ValueError("Invalid interval specified for 'backups': '{}'".format(backups))
            backups = pendulum.Interval(seconds=seconds)
        else:
            raise ValueError("Cannot parse 'backups' for objects of type '{}'".format(type(backups)))

        return backups

    @staticmethod
    def parse_size(size):
        if isinstance(size, str):
            reg = r'^([e\+\-\.\d]+?)\s*([kmgtpezy])?(i)?(b)?$'
            match = re.match(reg, size.strip(), flags=re.I)
            if not match:
                raise ValueError("Invalid size specified: '{}'".format(size))
            s, u, i, b = match.groups()
            s = float(s)
            u = 'kmgtpezy'.index(u.lower()) + 1 if u else 0
            i = 1024 if i else 1000
            b = {'b': 8, 'B': 1}[b] if b else 1
            size = s * i**u / b

        if not isinstance(size, Number):
            raise ValueError("Cannot parse 'size' for objects of type '{}'".format(type(size)))

        return size

    @staticmethod
    def parse_when(when):
        day = time = interval = None
        if isinstance(when, str):
            when_ = when.strip()
            reg = r'(?:({0})\s*({1})?|({1})\s*({0})?)'.format(r'w[0-6]', r'[\d\.\:\,]+(?:\s*[ap]m)?')
            match = re.fullmatch(reg, when_, flags=re.I)
            if match:
                w1, t1, t2, w2 = match.groups()
                w, t = (w1, t1) if (w2 is None and t2 is None) else (w2, t2)
                day = int(w[1]) if w else None
                date = pendulum.parse(t if t else '0', strict=True)
                time = pendulum.Time(date.hour, date.minute, date.second, date.microsecond)
            else:
                if all(c.isalpha() for c in when_):
                    when_ = '1 ' + when_
                seconds = FileSink.parse_duration(when_)
                if seconds is None:
                    raise ValueError("Invalid time or interval specified for 'when': '{}'".format(when))
                interval = pendulum.Interval(seconds=seconds)
        elif isinstance(when, datetime.timedelta):
            interval = pendulum.Interval.instance(when)
        elif isinstance(when, (datetime.datetime, datetime.time)):
            time = pendulum.Time(when.hour, when.minute, when.second, when.microsecond)
        elif isinstance(when, Number):
            interval = pendulum.Interval(hours=when)
        else:
            raise ValueError("Cannot parse 'when' for objects of type '{}'".format(type(when)))

        return day, time, interval

    @staticmethod
    def parse_duration(duration):
        duration = duration.strip()
        reg = r'(?:\s*([e\+\-\.\d]+)\s*([a-z]+)[\s\,\/]*)'
        if not re.fullmatch(reg + '+', duration, flags=re.I):
            return None

        units = [
            ('y|years?', 31536000),
            ('mo|months?', 2628000),
            ('w|weeks?', 604800),
            ('d|days?', 86400),
            ('h|hours?', 3600),
            ('m|minutes?', 60),
            ('s|seconds?', 1),
            ('ms|milliseconds?', 0.001),
            ('us|microseconds?', 0.000001),
        ]

        total = 0

        for value, unit in re.findall(reg, duration, flags=re.I):
            try:
                value = float(value)
            except ValueError:
                return None

            try:
                unit = next(u for r, u in units if re.fullmatch(r, unit, flags=re.I))
            except StopIteration:
                return None

            total += value * unit

        return total

    def rotating_write(self, message):
        if self.should_rollover(message):
            self.rollover()
        self.file.write(message)

    def should_rollover_size(self, file, message):
        # See https://github.com/python/cpython/blob/277c84067ff5dfa271725ee9da1a9d75a7c0bcd8/Lib/logging/handlers.py#L174-L188
        file.seek(0, 2)
        return file.tell() + len(message) >= self.rollover_size

    def next_rollover_time(self, current_rollover, time):
        if current_rollover is None:
            rollover_time = self.rollover_time
            if rollover_time is None:
                current_rollover = self.start_time
            else:
                start_time = self.start_time
                year, month, day = start_time.year, start_time.month, start_time.day
                hour, minute, second, microsecond = rollover_time.hour, rollover_time.minute, rollover_time.second, rollover_time.microsecond
                current_rollover = pendulum.create(year=year, month=month, day=day, hour=hour, minute=minute, second=second, microsecond=microsecond)

        if self.rollover_interval is not None:
            while current_rollover <= time:
                current_rollover += self.rollover_interval
            return current_rollover

        if self.rollover_day is None:
            while current_rollover <= time:
                current_rollover = current_rollover.add(days=1)
            return current_rollover

        days_names = ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY']
        day = [getattr(pendulum, day) for day in days_names][self.rollover_day]

        while current_rollover <= time:
            current_rollover = current_rollover.next(day, keep_time=True)
        return current_rollover

    def should_rollover(self, message):
        if self.size_based_rollover and self.should_rollover_size(self.file, message):
            return True

        if self.when_based_rollover and message.record['time'] >= self.rollover_at:
            self.rollover_at = self.next_rollover_time(self.rollover_at, message.record['time'])
            patch_datetime_file(self.rollover_at)
            return True

        return False

    def rollover(self):
        if self.file is not None:
            self.file.close()
        file_path = os.path.abspath(self.format_path())
        file_dir = os.path.dirname(file_path)

        os.makedirs(file_dir, exist_ok=True)

        if self.rotating and self.created > 0:
            if self.backups != math.inf:
                with os.scandir(file_dir) as it:
                    logs = [f for f in it if f.is_file() and self.regex_file_name.fullmatch(f.name)]

                if isinstance(self.backups, datetime.timedelta):
                    t = now().timestamp()
                    limit = t - self.backups.total_seconds()
                    for log in logs:
                        if log.stat().st_mtime <= limit:
                            os.remove(log)
                elif len(logs) > self.backups:
                    logs.sort(key=lambda log: (-log.stat().st_mtime, log.name))
                    for log in logs[self.backups:]:
                        os.remove(log)

            if os.path.exists(file_path):
                basename = os.path.basename(file_path)
                reg = re.escape(basename) + '\.\d+'
                with os.scandir(file_dir) as it:
                    logs = [f for f in it if f.is_file() and re.fullmatch(reg, f.name)]
                    logs.sort(key=lambda f: -int(f.name.split('.')[-1]))

                n = len(logs) + 1
                z = len(str(n))
                for i, log in enumerate(logs):
                    j = n - i
                    os.replace(log.path, file_path + '.' + str(j).zfill(z))
                os.replace(file_path, file_path + "." + "1".zfill(z))

        self.file = open(file_path, **self.kwargs)
        self.created += 1

class Logger:

    def __init__(self):
        self.handlers_count = 0
        self.handlers = {}

    def log_to(self, sink, *, level=DEBUG, format=VERBOSE_FORMAT, filter=None, colored=None, better_exceptions=True, **kwargs):
        if isclass(sink):
            sink = sink(**kwargs)
            return self.log_to(sink, level=level, format=format, filter=filter, colored=colored, better_exceptions=better_exceptions)
        elif callable(sink):
            if kwargs:
                writter = lambda m: sink(m, **kwargs)
            else:
                writter = sink
            if colored is None:
                colored = False
        elif isinstance(sink, (str, PathLike)):
            path = sink
            sink = FileSink(path, **kwargs)
            return self.log_to(sink, level=level, format=format, filter=filter, colored=colored, better_exceptions=better_exceptions)
        elif hasattr(sink, 'write') and callable(sink.write):
            sink_write = sink.write
            if kwargs:
                write = lambda m: sink_write(m, **kwargs)
            else:
                write = sink_write

            if hasattr(sink, 'flush') and callable(sink.flush):
                sink_flush = sink.flush
                writter = lambda m: write(m) and sink_flush()
            else:
                writter = write

            if colored is None:
                try:
                    colored = sink.isatty()
                except Exception:
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

        self.handlers[self.handlers_count] = (sink, handler)
        self.handlers_count += 1

        return self.handlers_count - 1

    def stop(self, handler_id=None):
        if handler_id is None:
            for sink, _ in self.handlers.values():
                if hasattr(sink, 'stop') and callable(sink.stop):
                    sink.stop()
            count = len(self.handlers)
            self.handlers.clear()
            return count
        elif handler_id in self.handlers:
            sink, _ = self.handlers.pop(handler_id)
            if hasattr(sink, 'stop') and callable(sink.stop):
                sink.stop()
            return 1

        return 0

    @staticmethod
    def make_log_function(level, log_exception=False):

        level_name = getLevelName(level)

        def log_function(self, message, *args, **kwargs):
            frame = get_frame(1)
            name = frame.f_globals['__name__']

            # TODO: Early exit if no handler

            now_ = now()
            patch_datetime(now_)

            message = message.format(*args, **kwargs)

            code = frame.f_code
            file_path = normcase(code.co_filename)
            file_name = basename(file_path)
            thread = current_thread()
            process = current_process()
            diff = now_ - start_time
            elapsed = pendulum.Interval(microseconds=diff.microseconds)

            level_recattr = LevelRecattr(level_name)
            level_recattr.no, level_recattr.name = level, level_name

            file_recattr = FileRecattr(file_name)
            file_recattr.name, file_recattr.path = file_name, file_path

            thread_recattr = ThreadRecattr(thread.ident)
            thread_recattr.id, thread_recattr.name = thread.ident, thread.name

            process_recattr = ProcessRecattr(process.ident)
            process_recattr.id, process_recattr.name = process.ident, process.name

            exception = exc_info() if log_exception else None

            record = {
                'name': name,
                'message': message,
                'time': now_,
                'elapsed': elapsed,
                'line': frame.f_lineno,
                'level': level_recattr,
                'file': file_recattr,
                'function': code.co_name,
                'module': splitext(file_name)[0],
                'thread': thread_recattr,
                'process': process_recattr,
                'exception': exception,
            }

            for _, handler in self.handlers.values():
                handler.emit(record)

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
