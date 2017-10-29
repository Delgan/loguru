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

DAYS_NAMES = ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY']

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

    def __init__(self, path, *, rotation=None, backups=None, **kwargs):
        self.start_time = now()
        patch_datetime_file(self.start_time)
        self.kwargs = kwargs.copy()
        self.kwargs.setdefault('mode', 'a')
        self.kwargs.setdefault('buffering', 1)
        self.path = str(path)
        self.file = None
        self.created = 0
        self.rotation_time = None

        self.should_rotate = self.make_should_rotate_function(rotation)
        self.manage_backups = self.make_manage_backups_function(backups)
        self.regex_file_name = self.make_regex_file_name(os.path.basename(self.path))

        self.rotate()

        if self.should_rotate is None:
            self.write = self.file.write
        else:
            self.write = self.rotating_write

    def stop(self):
        if self.file is not None:
            # compress
            self.file.close()
            self.file = None

    def format_path(self):
        now_ = now()
        patch_datetime_file(now_)

        info = {
            "time": now_,
            "start_time": self.start_time,
            "rotation_time": self.rotation_time,
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

    def make_should_rotate_function(self, rotation):
        if rotation is None:
            return None
        elif isinstance(rotation, str):
            size = self.parse_size(rotation)
            if size is not None:
                return self.make_should_rotate_function(size)
            interval = self.parse_duration(rotation)
            if interval is not None:
                return self.make_should_rotate_function(interval)
            daytime = self.parse_daytime(rotation)
            if daytime is not None:
                day, time = daytime
                if day is None:
                    return self.make_should_rotate_function(time)
                elif time is None:
                    time = pendulum.parse('00:00', strict=True)
                day = getattr(pendulum, DAYS_NAMES[day])
                time_limit = self.start_time.at(time.hour, time.minute, time.second, time.microsecond)
                if time_limit <= self.start_time:
                    time_limit = time_limit.next(day, keep_time=True)
                self.rotation_time = time_limit
                def function(message):
                    nonlocal time_limit
                    record_time = message.record['time']
                    if record_time >= time_limit:
                        while time_limit <= record_time:
                            time_limit = time_limit.next(day, keep_time=True)
                        self.rotation_time = time_limit
                        return True
                    return False
            else:
                raise ValueError("Cannot parse rotation from: '%s'" % rotation)
        elif isinstance(rotation, Number):
            size_limit = rotation
            def function(message):
                file = self.file
                file.seek(0, 2)
                return file.tell() + len(message) >= size_limit
        elif isinstance(rotation, datetime.time):
            time = pendulum.Time.instance(rotation)
            time_limit = self.start_time.at(time.hour, time.minute, time.second, time.microsecond)
            if time_limit <= self.start_time:
                time_limit.add(days=1)
            self.rotation_time = time_limit
            def function(message):
                nonlocal time_limit
                record_time = message.record['time']
                if record_time >= time_limit:
                    while time_limit <= record_time:
                        time_limit = time_limit.add(days=1)
                    self.rotation_time = time_limit
                    return True
                return False
        elif isinstance(rotation, datetime.timedelta):
            time_delta = pendulum.Interval.instance(rotation)
            time_limit = self.start_time + time_delta
            self.rotation_time = time_limit
            def function(message):
                nonlocal time_limit
                record_time = message.record['time']
                if record_time >= time_limit:
                    while time_limit <= record_time:
                        time_limit += time_delta
                    self.rotation_time = time_limit
                    return True
                return False
        elif callable(rotation):
            time_limit = rotation(self.start_time)
            def function(message):
                nonlocal time_limit
                record_time = message.record['time']
                if record_time >= time_limit:
                    time_limit = rotation(record_time)
                    self.rotation_time = time_limit
                    return True
                return False
        else:
            raise ValueError("Cannot infer rotation for objects of type: '%s'" % type(rotation))

        return function

    def make_manage_backups_function(self, backups):
        if backups is None:
            return None
        elif isinstance(backups, str):
            interval = self.parse_duration(backups)
            if interval is None:
                raise ValueError("Cannot parse backups from: '%s'" % backups)
            return self.make_manage_backups_function(interval)
        elif isinstance(backups, int):
            def function(logs):
                return sorted(logs, key=lambda log: (-log.stat().st_mtime, log.name))[backups:]
        elif isinstance(backups, datetime.timedelta):
            seconds = backups.total_seconds()
            def function(logs):
                t = now().timestamp()
                limit = t - seconds
                return [log for log in logs if log.stat().st_mtime <= limit]
        elif callable(backups):
            function = backups
        else:
            raise ValueError("Cannot infer backups for objects of type: '%s'" % type(backups))

        return function

    @staticmethod
    def parse_daytime(daytime):
        daytime = daytime.strip()

        daytime_reg = re.compile(r'(.*?)\s+at\s+(.*)', flags=re.I)
        day_reg = re.compile(r'w\d+', flags=re.I)
        time_reg = re.compile(r'[\d\.\:\,]+(?:\s*[ap]m)?', flags=re.I)

        daytime_match = daytime_reg.fullmatch(daytime)
        if daytime_match:
            day, time = daytime_match.groups()
        elif time_reg.fullmatch(daytime):
            day, time = None, daytime
        elif day_reg.fullmatch(daytime) or daytime.upper() in DAYS_NAMES:
            day, time = daytime, None
        else:
            return None

        if day is not None:
            if day_reg.fullmatch(day):
                day = int(day[1:])
                if not 0 <= day <= 6:
                    raise ValueError("Invalid weekday index while parsing daytime: '%d'" % day)
            elif day.upper() in DAYS_NAMES:
                day = DAYS_NAMES.index(day.upper())
            else:
                raise ValueError("Invalid weekday value while parsing daytime: '%s'" % day)

        if time is not None:
            time_ = time
            try:
                time = pendulum.parse(time, strict=True)
            except Exception as e:
                raise ValueError("Invalid time while parsing daytime: '%s'" % time) from e
            else:
                if not isinstance(time, datetime.time):
                    raise ValueError("Cannot strictly parse time from: '%s'" % time_)

        return day, time

    @staticmethod
    def parse_size(size):
        size = size.strip()
        reg = r'([e\+\-\.\d]+)\s*([kmgtpezy])?(i)?(b)'
        match = re.fullmatch(reg, size, flags=re.I)
        if not match:
            return None
        s, u, i, b = match.groups()
        try:
            s = float(s)
        except ValueError:
            raise ValueError("Invalid float value while parsing size: '%s'" % s)
        u = 'kmgtpezy'.index(u.lower()) + 1 if u else 0
        i = 1024 if i else 1000
        b = {'b': 8, 'B': 1}[b] if b else 1
        size = s * i**u / b

        return size

    @staticmethod
    def parse_duration(duration):
        duration = duration.strip()

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

        reg = r'(?:([e\+\-\.\d]+)\s*([a-z]+)[\s\,]*)'
        if not re.fullmatch(reg + '+', duration, flags=re.I):
            return None

        seconds = 0

        for value, unit in re.findall(reg, duration, flags=re.I):
            try:
                value = float(value)
            except ValueError:
                raise ValueError("Invalid float value while parsing duration: '%s'" % value)

            try:
                unit = next(u for r, u in units if re.fullmatch(r, unit, flags=re.I))
            except StopIteration:
                raise ValueError("Invalid unit value while parsing duration: '%s'" % unit)

            seconds += value * unit

        return pendulum.Interval(seconds=seconds)

    def rotating_write(self, message):
        if self.should_rotate(message):
            self.rotate()
        self.file.write(message)

    def rotate(self):
        self.stop()
        file_path = os.path.abspath(self.format_path())
        file_dir = os.path.dirname(file_path)

        os.makedirs(file_dir, exist_ok=True)

        if self.manage_backups is not None:
            regex_file_name = self.regex_file_name
            with os.scandir(file_dir) as it:
                logs = [f for f in it if regex_file_name.fullmatch(f.name) and f.is_file()]

            for log in self.manage_backups(logs):
                os.remove(log.path)

        if self.created > 0 and os.path.exists(file_path):
            basename = os.path.basename(file_path)
            reg = re.escape(basename) + '\.\d+'
            with os.scandir(file_dir) as it:
                logs = [f for f in it if f.is_file() and re.fullmatch(reg, f.name)]
            logs.sort(key=lambda f: -int(f.name.split('.')[-1]))

            n = len(logs) + 1
            z = len(str(n))
            for i, log in enumerate(logs):
                os.replace(log.path, file_path + '.%s' % str(n - i).zfill(z))
            os.replace(file_path, file_path + ".%s" % "1".zfill(z))

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
