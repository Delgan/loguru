import datetime
import decimal
import numbers
import os
import re
import shutil
import string

import pendulum
from pendulum import now as pendulum_now

DAYS_NAMES = ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY']


class FileSink:

    def __init__(self, path, *, rotation=None, backups=None, compression=None, **kwargs):
        self.start_time = pendulum_now()
        self.start_time._FORMATTER = 'alternative'
        self.start_time._to_string_format = '%Y-%m-%d_%H-%M-%S'
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
        now = pendulum_now()
        now._FORMATTER = 'alternative'
        now._to_string_format = '%Y-%m-%d_%H-%M-%S'

        if self.rotation_time:
            self.rotation_time._FORMATTER = 'alternative'
            self.rotation_time._to_string_format = '%Y-%m-%d_%H-%M-%S'

        record = {
            "time": now,
            "start_time": self.start_time,
            "rotation_time": self.rotation_time,
            "n": self.created,
            "n+1": self.created + 1,
        }

        return self.path.format_map(record)

    @staticmethod
    def make_regex_file_name(file_name):
        tokens = string.Formatter().parse(file_name)
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
        elif isinstance(rotation, (numbers.Real, decimal.Decimal)):
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
            raise ValueError("Cannot infer rotation for objects of type: '%s'" % type(rotation).__name__)

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
                t = pendulum_now().timestamp()
                limit = t - seconds
                return [log for log in logs if log.stat().st_mtime <= limit]
        elif callable(backups):
            function = backups
        else:
            raise ValueError("Cannot infer backups for objects of type: '%s'" % type(backups).__name__)

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
            raise ValueError("Cannot infer compression for objects of type: '%s'" % type(compression).__name__)

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
