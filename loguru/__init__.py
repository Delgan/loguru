import datetime
from inspect import isclass
from os import getpid, PathLike
from os.path import normcase, basename, splitext
import sys
from sys import exc_info, stdout as STDOUT, stderr as STDERR
from multiprocessing import current_process
from threading import current_thread
import traceback
import numbers
import decimal
import shutil
import re
import os
import glob
import random
from collections import defaultdict, OrderedDict
from string import Formatter
import math
import functools
import importlib
import atexit

import ansimarkup
from better_exceptions_fork import ExceptionFormatter
from pendulum import now
import pendulum

VERBOSE_FORMAT = "<green>{time}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"

DAYS_NAMES = ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY']

__version__ = "0.0.1"

start_time = now()

Real = (numbers.Real, decimal.Decimal)

def getframe_fallback(n):
    """Return the frame object for the caller's stack frame."""
    try:
        raise Exception
    except Exception:
        frame = exc_info()[2].tb_frame.f_back
        for _ in range(n):
            frame = frame.f_back
        return frame

def get_getframe_function():
    if hasattr(sys, '_getframe'):
        getframe = sys._getframe
    else:
        getframe = getframe_fallback
    return getframe

getframe = get_getframe_function()

def patch_datetime(date):
    date._FORMATTER = 'alternative'

def patch_datetime_file(date):
    date._FORMATTER = 'alternative'
    date._to_string_format = '%Y-%m-%d_%H-%M-%S'

class loguru_traceback:
    __slots__ = ('tb_frame', 'tb_lasti', 'tb_lineno', 'tb_next', '__is_caught_point__')

    def __init__(self, frame, lasti, lineno, next_=None, is_caught_point=False):
        self.tb_frame = frame
        self.tb_lasti = lasti
        self.tb_lineno = lineno
        self.tb_next = next_
        self.__is_caught_point__ = is_caught_point

class StrRecord(str):
    pass

class HackyInt(int):

    rand = '0' + str(random.randrange(10**32, 10**33))

    def __str__(self):
        return self.rand

    def __eq__(self, other):
        return False

class Handler:

    def __init__(self, *, writter, levelno, format_, filter_, colored, better_exceptions, levelname_to_color={}):
        self.writter = writter
        self.levelno = levelno
        self.format = format_
        self.filter = filter_
        self.colored = colored
        self.better_exceptions = better_exceptions

        if colored:
            self.decolorized_format = None
            self.precolorized_formats = self.precolorize_formats(levelname_to_color)
        else:
            self.decolorized_format = self.decolorize(format_)
            self.precolorized_formats = None

        self.exception_formatter = ExceptionFormatter(colored=colored)

    @staticmethod
    def make_ansimarkup(color):
        color = ansimarkup.parse(color)
        custom_markup = dict(level=color, lvl=color)
        am = ansimarkup.AnsiMarkup(tags=custom_markup)
        return am

    @staticmethod
    def decolorize(format_):
        am = Handler.make_ansimarkup('')
        return am.strip(format_)

    @staticmethod
    def colorize(format_, color):
        am = Handler.make_ansimarkup(color)
        return am.parse(format_)

    def update_format(self, levelname, color):
        if not self.colored:
            return
        self.precolorized_formats[levelname] = self.colorize(self.format, color)

    def precolorize_formats(self, levelname_to_color):
        precolorized = self.colorize(self.format, '')
        precomputed_formats = defaultdict(lambda: precolorized)

        for levelname, color in levelname_to_color.items():
            precomputed_formats[levelname] = self.colorize(self.format, color)

        return precomputed_formats

    def emit(self, record, exception=None):
        level = record['level']
        if self.levelno > level.no:
            return

        if self.filter is not None:
            if not self.filter(record):
                return

        if self.colored:
            precomputed_format = self.precolorized_formats[level.name]
        else:
            precomputed_format = self.decolorized_format

        formatted = precomputed_format.format_map(record) + '\n'

        if exception:
            hacky_int = None
            tb = exception[2]
            while tb:
                if tb.__is_caught_point__:
                    hacky_int = HackyInt(tb.tb_lineno)
                    tb.tb_lineno = hacky_int
                    break
                tb = tb.tb_next

            if self.better_exceptions:
                formatted_exc = self.exception_formatter.format_exception(*exception)
            else:
                formatted_exc = traceback.format_exception(*exception)

            formatted_exc = ''.join(formatted_exc)

            reg = r'(?:^\S*(Traceback \(most recent call last\):)\S*$|^\S*  \S*File.*\D(%s)\D.*$)' % str(hacky_int)
            matches = re.finditer(reg, formatted_exc, flags=re.M)

            tb_match = None

            for match in matches:
                tb, line = match.groups()
                if tb is not None:
                    tb_match = match
                if line is not None:
                    s, e = match.span(2)
                    formatted_exc = formatted_exc[:s] + str(int(hacky_int)) + formatted_exc[e:]
                    s = match.start(0)
                    formatted_exc = formatted_exc[:s] + formatted_exc[s:].replace(" ", ">", 1)
                    if tb_match is not None:
                        old = "Traceback (most recent call last):"
                        new = "Traceback (most recent call last, catch point marked):"
                        s = tb_match.start(0)
                        formatted_exc = formatted_exc[:s] + formatted_exc[s:].replace(old, new, 1)
                    break

            formatted += formatted_exc


        message = StrRecord(formatted)
        message.record = record

        self.writter(message)

class LevelRecattr(str):
    __slots__ = ('no', 'name', 'icon')


class FileRecattr(str):
    __slots__ = ('name', 'path')


class ThreadRecattr(str):
    __slots__ = ('id', 'name')


class ProcessRecattr(str):
    __slots__ = ('id', 'name')


class FileSink:

    def __init__(self, path, *, rotation=None, backups=None, compression=None, **kwargs):
        self.start_time = now()
        patch_datetime_file(self.start_time)
        self.kwargs = kwargs.copy()
        self.kwargs.setdefault('mode', 'a')
        self.kwargs.setdefault('buffering', 1)
        self.path = str(path)
        self.file = None
        self.file_path = None
        self.created = 0
        self.rotation_time = None

        self.should_rotate = self.make_should_rotate_function(rotation)
        self.manage_backups = self.make_manage_backups_function(backups)
        self.compress_file = self.make_compress_file_function(compression)
        self.regex_file_name = self.make_regex_file_name(os.path.basename(self.path))

        self.rotate()

        if self.should_rotate is None:
            self.write = self.file.write
        else:
            self.write = self.rotating_write

    def format_path(self):
        now_ = now()
        patch_datetime_file(now_)

        record = {
            "time": now_,
            "start_time": self.start_time,
            "rotation_time": self.rotation_time,
            "n": self.created,
            "n+1": self.created + 1,
        }

        return self.path.format_map(record)

    @staticmethod
    def make_regex_file_name(file_name):
        tokens = Formatter().parse(file_name)
        regex_name = ''.join(re.escape(t[0]) + '.*' * (t[1] is not None) for t in tokens)
        regex_name += '(?:\.\d+)?'
        regex_name += '(?:\.(?:gz(?:ip)?|bz(?:ip)?2|xz|lzma|zip))?'
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
            frequency = self.parse_frequency(rotation)
            if frequency is not None:
                return self.make_should_rotate_function(frequency)
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
        elif isinstance(rotation, Real):
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

    def make_compress_file_function(self, compression):
        if compression is None or compression is False:
            return None
        elif compression is True:
            return self.make_compress_file_function('gz')
        elif isinstance(compression, str):
            compress_format = compression.strip().lstrip('.')
            compress_format_lower = compress_format.lower()

            compress_module = None
            compress_args = {}
            compress_func = shutil.copyfileobj

            if compress_format_lower in ['gz', 'gzip']:
                import gzip
                compress_module = gzip
            elif compress_format_lower in ['bz2', 'bzip2']:
                import bz2
                compress_module = bz2
            elif compress_format_lower == 'xz':
                import lzma
                compress_module = lzma
                compress_args = dict(format=lzma.FORMAT_ALONE)
            elif compress_format_lower == 'lzma':
                import lzma
                compress_module = lzma
                compress_args = dict(format=lzma.FORMAT_XZ)
            elif compress_format_lower == 'zip':
                import zlib  # Used by zipfile, so check it's available
                import zipfile
                def func(path):
                    compress_path = '%s.%s' % (path, compress_format)
                    with zipfile.ZipFile(compress_path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
                        z.write(path)
                    os.remove(path)
                return func
            else:
                raise ValueError("Invalid compression format: '%s'" % compress_format)

            def func(path):
                with open(path, 'rb') as f_in:
                    compress_path = '%s.%s' % (path, compress_format)
                    with compress_module.open(compress_path, 'wb', **compress_args) as f_out:
                        compress_func(f_in, f_out)
                os.remove(path)

            return func

        elif callable(compression):
            return compression
        else:
            raise ValueError("Cannot infer compression for objects of type: '%s'" % type(compression))

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

    @staticmethod
    def parse_frequency(frequency):
        frequency = frequency.strip().lower()
        function = None

        if frequency == 'hourly':
            function = lambda t: t.add(hours=1).start_of('hour')
        elif frequency == 'daily':
            function = '00:00'
        elif frequency == 'weekly':
            function = 'w0'
        elif frequency == 'monthly':
            function = lambda t: t.add(months=1).start_of('month')
        elif frequency == 'yearly':
            function = lambda t: t.add(years=1).start_of('year')

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

    def rotating_write(self, message):
        if self.should_rotate(message):
            self.rotate()
        self.file.write(message)

    def rotate(self):
        old_path = self.file_path
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
            reg = re.escape(basename) + '(?:\.(\d+))?(\.(?:gz(?:ip)?|bz(?:ip)?2|xz|lzma|zip))?'
            reg = re.compile(reg, flags=re.I)
            with os.scandir(file_dir) as it:
                logs = [f for f in it if f.is_file() and reg.fullmatch(f.name) and f.name != basename]
            logs.sort(key=lambda f: -int(reg.fullmatch(f.name).group(1) or 0))

            n = len(logs) + 1
            z = len(str(n))
            for i, log in enumerate(logs):
                num = '.%s' % str(n - i).zfill(z)
                ext = reg.fullmatch(log.name).group(2) or ''
                os.replace(log.path, file_path + num + ext)
            new_path = file_path + ".%s" % "1".zfill(z)
            os.replace(file_path, new_path)

            if file_path == old_path:
                old_path = new_path

        if self.compress_file is not None and old_path is not None and os.path.exists(old_path):
            self.compress_file(old_path)

        self.file = open(file_path, **self.kwargs)
        self.file_path = file_path
        self.created += 1

    def stop(self):
        if self.file is not None:
            if self.compress_file is not None and self.should_rotate is None:
                self.compress_file(self.file_path)
            self.file.close()
            self.file = None
            self.file_path = None

class Catcher:

    def __init__(self, logger, exception=BaseException, *, level=None, reraise=False,
                       message="An error has been caught in function '{function}', "
                               "process '{process.name}' ({process.id}), "
                               "thread '{thread.name}' ({thread.id}):"):
        self.logger = logger
        self.exception = exception
        self.level = level
        self.reraise = reraise
        self.message = message

        self.function_name = None
        self.exception_logger = self.logger.exception

    def __enter__(self):
        pass

    def __exit__(self, type_, value, traceback_):
        if type_ is None:
            return

        if not issubclass(type_, self.exception):
            return False

        thread = current_thread()
        thread_recattr = ThreadRecattr(thread.ident)
        thread_recattr.id, thread_recattr.name = thread.ident, thread.name

        process = current_process()
        process_recattr = ProcessRecattr(process.ident)
        process_recattr.id, process_recattr.name = process.ident, process.name

        function_name = self.function_name
        if function_name is None:
            function_name = getframe(1).f_code.co_name

        record = {
            'process': process_recattr,
            'thread': thread_recattr,
            'function': function_name,
        }

        if self.level is not None: # pragma: no cover
            # TODO: Use logger function accordingly
            raise NotImplementedError

        self.exception_logger(self.message.format_map(record))

        return not self.reraise

    def __call__(self, *args, **kwargs):
        if not kwargs and len(args) == 1:
            arg = args[0]
            if callable(arg) and (not isclass(arg) or not issubclass(arg, BaseException)):
                function = arg
                function_name = function.__name__

                @functools.wraps(function)
                def catch_wrapper(*args, **kwargs):
                    # TODO: Fix it to avoid any conflict with threading because of self modification
                    self.function_name = function_name
                    self.exception_logger = self.logger._exception_catcher
                    with self:
                        function(*args, **kwargs)
                    self.function_name = None
                    self.exception_logger = self.logger.exception

                return catch_wrapper

        return Catcher(self.logger, *args, **kwargs)

class Logger:

    def __init__(self, *, dummy=None):
        self.dummy = dummy
        self.handlers_count = 0
        self.handlers = {}
        self.levels = {}
        self.catch = Catcher(self)

        self.add_level("TRACE", 5, "<cyan><bold>", "✏️")        # Pencil
        self.add_level("DEBUG", 10, "<blue><bold>", "🐞")        # Lady Beetle
        self.add_level("INFO", 20, "<bold>", "ℹ️")                # Information
        self.add_level("SUCCESS", 25, "<green><bold>", "✔️")   # Heavy Check Mark
        self.add_level("WARNING", 30, "<yellow><bold>", "⚠️")  # Warning
        self.add_level("ERROR", 40, "<red><bold>", "❌")          # Cross Mark
        self.add_level("CRITICAL", 50, "<RED><bold>", "☠️")   # Skull and Crossbones

        atexit.register(self.clear)

    def add_level(self, name, level, color="", icon=" "):
        if not isinstance(name, str):
            raise ValueError("Invalid level name, it should be a string, not: '%s'" % type(name))

        if not isinstance(level, int):
            raise ValueError("Invalid level value, it should be an int, not: '%s'" % type(level))

        if level < 0:
            raise ValueError("Invalid level value (%d), it should be a positive number" % level)

        name = name.upper()
        self.levels[name] = (level, color, icon)

        for _, handler in self.handlers.values():
            handler.update_format(name, color)


    def edit_level(self, name, level=None, color=None, icon=None):
        old_level, old_color, old_icon = self.get_level(name)

        if level is None:
            level = old_level

        if color is None:
            color = old_color

        if icon is None:
            icon = old_icon

        self.add_level(name, level, color, icon)

    def get_level(self, name):
        return self.levels[name.upper()]

    def log_to(self, sink, *, level="DEBUG", format=VERBOSE_FORMAT, filter=None, colored=None, better_exceptions=True, **kwargs):
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

        if isinstance(level, str):
            level = level.upper()
            levelno, _, _ = self.levels[level]
        elif isinstance(level, int):
            levelno = level
        else:
            raise ValueError("Invalid level, it should be an int or a string, not: '%s'" % type(level))

        if levelno < 0:
            raise ValueError("Invalid level value (%d), it should be a positive number" % levelno)

        handler = Handler(
            writter=writter,
            levelno=levelno,
            format_=format,
            filter_=filter,
            colored=colored,
            better_exceptions=better_exceptions,
            levelname_to_color={name: color for name, (_, color, _) in self.levels.items()},
        )

        self.handlers[self.handlers_count] = (sink, handler)
        self.handlers_count += 1

        return self.handlers_count - 1

    def clear(self, handler_id=None):
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

    def config(self, source=None, *, sinks=None, dummy=None):
        if source is None:
            dict_config = {}
        elif isinstance(source, dict):
            dict_config = source
        elif isinstance(source, (str, PathLike)):
            source = str(source)
            name = 'loguru.dynamic_config_loader'
            loader = importlib.machinery.SourceFileLoader(name, source)
            spec = importlib.util.spec_from_loader(name, loader)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            dict_config = module.config
        else:
            raise ValueError("Cannot get dict config for objects of type: '%s'" % type(source))

        kwargs = {
            'sinks': sinks,
            'dummy': dummy,
        }

        for key, value in kwargs.items():
            if value is not None:
                dict_config[key] = value

        self.clear()
        self.dummy = dict_config.get('dummy', False)
        sinks_ids = [self.log_to(**params) for params in dict_config.get('sinks', [])]

        return sinks_ids

    def log(_self, _level, _message, *args, **kwargs):
        function = _self.make_log_function(_level)
        function(_self, _message, *args, **kwargs)

    @staticmethod
    @functools.lru_cache()
    def make_log_function(level, log_exception=0):

        if isinstance(level, str):
            level_id = level_name = level.upper()
        elif isinstance(level, int):
            if level < 0:
                raise ValueError("Invalid level value (%d), it should be a positive number" % level)
            level_id = None
            level_name = 'Level %d' % level
        else:
            raise ValueError("Invalid level, it should be an int or a string, not: '%s'" % type(level))

        def log_function(_self, _message, *args, **kwargs):
            frame = getframe(1)
            name = frame.f_globals['__name__']

            # TODO: Early exit if no handler

            now_ = now()
            patch_datetime(now_)

            message = _message.format(*args, **kwargs)

            if level_id is None:
                level_no, level_icon = level, ' '
            else:
                level_no, _, level_icon = _self.levels[level_name]

            code = frame.f_code
            file_path = normcase(code.co_filename)
            file_name = basename(file_path)
            thread = current_thread()
            process = current_process()
            diff = now_ - start_time
            elapsed = pendulum.Interval(microseconds=diff.microseconds)

            level_recattr = LevelRecattr(level_name)
            level_recattr.no, level_recattr.name, level_recattr.icon = level_no, level_name, level_icon

            file_recattr = FileRecattr(file_name)
            file_recattr.name, file_recattr.path = file_name, file_path

            thread_recattr = ThreadRecattr(thread.ident)
            thread_recattr.id, thread_recattr.name = thread.ident, thread.name

            process_recattr = ProcessRecattr(process.ident)
            process_recattr.id, process_recattr.name = process.ident, process.name

            exception = None
            if log_exception:
                ex_type, ex, tb = exc_info()

                root_frame = tb.tb_frame.f_back

                # TODO: Test edge cases (look in CPython source code for traceback objects and exc.__traceback__ usages)

                loguru_tb = root_tb = None
                while tb:
                    if tb.tb_frame.f_code.co_filename != __file__:
                        new_tb = loguru_traceback(tb.tb_frame, tb.tb_lasti, tb.tb_lineno, None)
                        if loguru_tb:
                            loguru_tb.tb_next = new_tb
                        else:
                            root_tb = new_tb
                        loguru_tb = new_tb
                    tb = tb.tb_next

                caught_tb = root_tb

                while root_frame:
                    if root_frame.f_code.co_filename != __file__:
                        root_tb = loguru_traceback(root_frame, root_frame.f_lasti, root_frame.f_lineno, root_tb)
                    root_frame = root_frame.f_back

                if log_exception == 1:
                    caught_tb.__is_caught_point__ = True
                else:
                    tb_prev = tb_next = root_tb
                    while tb_next:
                        if tb_next == caught_tb:
                            break
                        tb_prev, tb_next = tb_next, tb_next.tb_next
                    tb_prev.__is_caught_point__ = True


                exception = (ex_type, ex, root_tb)

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
            }

            for _, handler in _self.handlers.values():
                handler.emit(record, exception)

        doc = "Log 'message.format(*args, **kwargs)' with severity '{}'.".format(level_name)
        if log_exception:
            doc += ' Log also current traceback.'
        log_function.__doc__ = doc

        return log_function

    trace = make_log_function.__func__("TRACE")
    debug = make_log_function.__func__("DEBUG")
    info = make_log_function.__func__("INFO")
    success = make_log_function.__func__("SUCCESS")
    warning = make_log_function.__func__("WARNING")
    error = make_log_function.__func__("ERROR")
    exception = make_log_function.__func__("ERROR", 1)
    _exception_catcher = make_log_function.__func__("ERROR", 2)
    critical = make_log_function.__func__("CRITICAL")

logger = Logger()
logger.log_to(STDERR)
