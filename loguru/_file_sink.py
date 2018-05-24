import datetime
import decimal
import glob
import numbers
import os
import random
import shutil
import string
import time

import base36
import pendulum

from . import _string_parsers
from ._fast_now import fast_now


class FileDateTime(pendulum.DateTime):

    def __format__(self, spec):
        if not spec:
            spec = "YYY-MM-DD_HH-mm-ss"
        return super().__format__(spec)

    @classmethod
    def now(cls):
        # TODO: Use FileDateTime.now() instead, when pendulum/#203 fixed
        t = fast_now()
        return cls(t.year, t.month, t.day, t.hour, t.minute, t.second, t.microsecond, t.tzinfo, fold=t.fold)


class FileSink:

    def __init__(self, path, *, rotation=None, retention=None, compression=None, delayed=False,
                 mode='a', buffering=1, **kwargs):
        self.start_time = FileDateTime.now()
        self.mode = mode
        self.buffering = buffering
        self.kwargs = kwargs.copy()
        self.path = str(path)
        self.file = None
        self.file_path = None
        self.created = 1

        self.rotation_function = self.make_rotation_function(rotation)
        self.retention_function = self.make_retention_function(retention)
        self.compression_function = self.make_compression_function(compression)
        self.glob_pattern = self.make_glob_pattern(self.path)

        if delayed:
            self.write = self.delayed_write
        else:
            self.initialize_write_function()

    def initialize_write_function(self):
        self.terminate(create_new=True)

        if self.rotation_function is None:
            self.write = self.file.write
        else:
            self.write = self.rotating_write

    def format_path(self):
        now = FileDateTime.now()

        record = {
            "time": now,
            "start_time": self.start_time,
            "n": self.created,
        }

        return os.path.abspath(self.path.format_map(record))

    @staticmethod
    def make_glob_pattern(path):
        tokens = string.Formatter().parse(path)
        parts = (glob.escape(text) + '*' * (name is not None) for text, name, *_ in tokens)
        root, ext = os.path.splitext(''.join(parts))
        if ext:
            pattern = root + '.*'
        else:
            pattern = root + '*'
        return pattern

    def make_rotation_function(self, rotation):

        def make_from_size(size_limit):
            def rotation_function(message, file):
                file.seek(0, 2)
                return file.tell() + len(message) >= size_limit
            return rotation_function

        def make_from_time(step_forward, time_init=None):
            time_limit = self.start_time
            if time_init is not None:
                t = time_init
                time_limit = time_limit.at(t.hour, t.minute, t.second, t.microsecond)
            if time_limit <= self.start_time:
                time_limit = step_forward(time_limit)
            def rotation_function(message, file):
                nonlocal time_limit
                record_time = message.record['time']
                if record_time >= time_limit:
                    while time_limit <= record_time:
                        time_limit = step_forward(time_limit)
                    return True
                return False
            return rotation_function

        if rotation is None:
            return None
        elif isinstance(rotation, str):
            size = _string_parsers.parse_size(rotation)
            if size is not None:
                return self.make_rotation_function(size)
            interval = _string_parsers.parse_duration(rotation)
            if interval is not None:
                return self.make_rotation_function(interval)
            frequency = _string_parsers.parse_frequency(rotation)
            if frequency is not None:
                return make_from_time(frequency)
            daytime = _string_parsers.parse_daytime(rotation)
            if daytime is not None:
                day, time = daytime
                if day is None:
                    return self.make_rotation_function(time)
                if time is None:
                    time = pendulum.parse('00:00', exact=True, strict=False)
                return make_from_time(lambda t: t.next(day, keep_time=True), time_init=time)
            raise ValueError("Cannot parse rotation from: '%s'" % rotation)
        elif isinstance(rotation, (numbers.Real, decimal.Decimal)):
            return make_from_size(rotation)
        elif isinstance(rotation, datetime.time):
            time = pendulum.Time(hour=rotation.hour, minute=rotation.minute,
                                 second=rotation.second, microsecond=rotation.microsecond,
                                 tzinfo=rotation.tzinfo, fold=rotation.fold)
            return make_from_time(lambda t: t.add(days=1), time_init=time)
        elif isinstance(rotation, datetime.timedelta):
            interval = pendulum.Duration(days=rotation.days, seconds=rotation.seconds,
                                         microseconds=rotation.microseconds)
            return make_from_time(lambda t: t + interval)
        elif callable(rotation):
            return rotation
        else:
            raise ValueError("Cannot infer rotation for objects of type: '%s'" % type(rotation).__name__)

    def make_retention_function(self, retention):

        def make_from_filter(filter_logs):
            def retention_function(logs):
                for log in filter_logs(logs):
                    os.remove(log)
            return retention_function

        if retention is None:
            return None
        elif isinstance(retention, str):
            interval = _string_parsers.parse_duration(retention)
            if interval is None:
                raise ValueError("Cannot parse retention from: '%s'" % retention)
            return self.make_retention_function(interval)
        elif isinstance(retention, int):
            key_log = lambda log: (-os.stat(log).st_mtime, log)
            def filter_logs(logs):
                return sorted(logs, key=key_log)[retention:]
            return make_from_filter(filter_logs)
        elif isinstance(retention, datetime.timedelta):
            seconds = retention.total_seconds()
            def filter_logs(logs):
                t = fast_now().timestamp()
                return [log for log in logs if os.stat(log).st_mtime <= t - seconds]
            return make_from_filter(filter_logs)
        elif callable(retention):
            return retention
        else:
            raise ValueError("Cannot infer retention for objects of type: '%s'" % type(retention).__name__)

    def make_compression_function(self, compression):

        def make_compress_generic(opener, **kwargs):
            def compress(path_in, path_out):
                with open(path_in, 'rb') as f_in:
                    with opener(path_out, 'wb', **kwargs) as f_out:
                        shutil.copyfileobj(f_in, f_out)
            return compress

        def make_compress_archive(mode):
            import tarfile
            def compress(path_in, path_out):
                with tarfile.open(path_out, 'w:' + mode) as f_comp:
                    f_comp.add(path_in, os.path.basename(path_in))
            return compress

        def make_compress_zipped():
            import zlib, zipfile
            def compress(path_in, path_out):
                with zipfile.ZipFile(path_out, 'w', compression=zipfile.ZIP_DEFLATED) as f_comp:
                    f_comp.write(path_in, os.path.basename(path_in))
            return compress

        if compression is None:
            return None
        elif isinstance(compression, str):
            ext = compression.strip().lstrip('.')

            if ext == 'gz':
                import zlib, gzip
                compress = make_compress_generic(gzip.open)
            elif ext == 'bz2':
                import bz2
                compress = make_compress_generic(bz2.open)
            elif ext == 'xz':
                import lzma
                compress = make_compress_generic(lzma.open, format=lzma.FORMAT_XZ)
            elif ext == 'lzma':
                import lzma
                compress = make_compress_generic(lzma.open, format=lzma.FORMAT_ALONE)
            elif ext == 'tar':
                compress = make_compress_archive('')
            elif ext == 'tar.gz':
                import zlib, gzip
                compress = make_compress_archive('gz')
            elif ext == 'tar.bz2':
                import bz2
                compress = make_compress_archive('bz2')
            elif ext == 'tar.xz':
                import lzma
                compress = make_compress_archive('xz')
            elif ext == 'zip':
                compress = make_compress_zipped()
            else:
                raise ValueError("Invalid compression format: '%s'" % ext)

            def compression_function(path_in):
                path_out = path_in + '.' + ext
                compress(path_in, path_out)
                os.remove(path_in)

            return compression_function
        elif callable(compression):
            return compression
        else:
            raise ValueError("Cannot infer compression for objects of type: '%s'" % type(compression).__name__)

    def rotating_write(self, message):
        if self.rotation_function(message, self.file):
            compress = self.compression_function is not None
            manage = self.retention_function is not None
            self.terminate(check_conflict=True, exec_compression=compress, exec_retention=manage, create_new=True)
        self.file.write(message)

    def delayed_write(self, message):
        self.initialize_write_function()
        self.write(message)

    def terminate(self, *, check_conflict=False, exec_compression=False, exec_retention=False, create_new=False):
        old_file = self.file
        old_path = self.file_path

        self.file = None
        self.file_path = None

        if old_file is not None:
            old_file.close()

        new_path = self.format_path()

        if check_conflict and new_path == old_path:
            time_part = base36.dumps(int(time.time() * 1000))
            rand_part = base36.dumps(int(random.random() * 36**4))
            log_id = "{:0>8}{:0>4}".format(time_part, rand_part).upper()
            root, ext = os.path.splitext(old_path)
            renamed_path = root + '.' + log_id + ext
            os.rename(old_path, renamed_path)
            old_path = renamed_path

        if exec_compression:
            self.compression_function(old_path)

        if exec_retention:
            logs = glob.glob(self.glob_pattern)
            self.retention_function(logs)

        if create_new:
            new_dir = os.path.dirname(new_path)
            os.makedirs(new_dir, exist_ok=True)
            self.file = open(new_path, mode=self.mode, buffering=self.buffering, **self.kwargs)
            self.file_path = new_path
            self.created += 1

    def stop(self):
        rotating = self.rotation_function is not None
        appending = 'a' in self.mode
        compression = (self.compression_function is not None) and (not rotating or not appending)
        retention = (self.retention_function is not None) and (not rotating or not appending)
        check = compression
        self.terminate(check_conflict=check, exec_compression=compression, exec_retention=retention, create_new=False)
