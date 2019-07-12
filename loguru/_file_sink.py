import datetime as datetime_
import decimal
import glob
import locale
import numbers
import os
import shutil
import string

from . import _string_parsers as string_parsers
from ._datetime import aware_now, datetime


class FileDateFormatter:
    def __init__(self, datetime=None):
        self.datetime = datetime or aware_now()

    def __format__(self, spec):
        if not spec:
            spec = "%Y-%m-%d_%H-%M-%S_%f"
        return self.datetime.__format__(spec)


class FileSink:
    def __init__(
        self,
        path,
        *,
        rotation=None,
        retention=None,
        compression=None,
        delay=False,
        mode="a",
        buffering=1,
        encoding=None,
        **kwargs
    ):
        self.encoding = locale.getpreferredencoding(False) if encoding is None else encoding
        self.name = str(path)

        self._kwargs = {**kwargs, "mode": mode, "buffering": buffering, "encoding": self.encoding}
        self._path = str(path)

        self._rotation_function, self._init_rotation = self._make_rotation_function(rotation)
        self._retention_function = self._make_retention_function(retention)
        self._compression_function = self._make_compression_function(compression)
        self._glob_pattern = self._make_glob_pattern(self._path)
        self._get_creation_time = self._make_get_creation_time_function()
        self._set_creation_time = self._make_set_creation_time_function()

        self._file = None
        self._file_path = None

        if not delay:
            self._initialize_file(rename_existing=False)
            if self._init_rotation is not None:
                self._init_rotation(self._file_path)

    def write(self, message):
        if self._file is None:
            self._initialize_file(rename_existing=False)
            if self._init_rotation is not None:
                self._init_rotation(self._file_path)

        if self._rotation_function is not None and self._rotation_function(message, self._file):
            self._terminate(teardown=True)
            self._initialize_file(rename_existing=True)
            if self._set_creation_time is not None:
                self._set_creation_time(self._file_path, datetime.now().timestamp())

        self._file.write(message)

    def _initialize_file(self, *, rename_existing):
        new_path = self._path.format_map({"time": FileDateFormatter()})
        new_path = os.path.abspath(new_path)
        new_dir = os.path.dirname(new_path)
        os.makedirs(new_dir, exist_ok=True)

        if rename_existing and os.path.isfile(new_path):
            creation_time = self._get_creation_time(new_path)
            creation_datetime = datetime.fromtimestamp(creation_time)
            date = FileDateFormatter(creation_datetime)
            root, ext = os.path.splitext(new_path)
            renamed_path = "{}.{}{}".format(root, date, ext)
            os.rename(new_path, renamed_path)

        self._file_path = new_path
        self._file = open(new_path, **self._kwargs)

    @staticmethod
    def _make_glob_pattern(path):
        tokens = string.Formatter().parse(path)
        parts = (glob.escape(text) + "*" * (name is not None) for text, name, *_ in tokens)
        root, ext = os.path.splitext("".join(parts))
        if ext:
            pattern = root + ".*"
        else:
            pattern = root + "*"
        return pattern

    @staticmethod
    def _make_get_creation_time_function():
        def get_creation_time_windows(filepath):
            return os.stat(filepath).st_ctime

        def get_creation_time_darwin(filepath):
            return os.stat(filepath).st_birthtime

        def get_creation_time_linux(filepath):
            try:
                return float(os.getxattr(filepath, b"user.loguru_crtime"))
            except OSError:
                return os.stat(filepath).st_mtime

        if os.name == "nt":
            return get_creation_time_windows
        elif hasattr(os.stat_result, "st_birthtime"):
            return get_creation_time_darwin
        else:
            return get_creation_time_linux

    @staticmethod
    def _make_set_creation_time_function():
        def set_creation_time_darwin(filepath, timestamp):
            try:
                os.setxattr(filepath, b"user.loguru_crtime", str(timestamp).encode("ascii"))
            except OSError:
                pass

        if os.name == "nt":
            import win32_setctime

            if win32_setctime.SUPPORTED:
                return win32_setctime.setctime
            else:
                return None
        elif hasattr(os.stat_result, "st_birthtime"):
            return None
        else:
            return set_creation_time_darwin

    def _make_rotation_function(self, rotation):
        def make_from_size(size_limit):
            def rotation_function(message, file):
                file.seek(0, 2)
                return file.tell() + len(message) >= size_limit

            return rotation_function, None

        def make_from_time(step_forward, time_init=None):

            time_limit = None

            def init_time_rotation(filepath):
                nonlocal time_limit
                creation_time = self._get_creation_time(filepath)
                if self._set_creation_time is not None:
                    self._set_creation_time(filepath, creation_time)
                start_time = time_limit = datetime.fromtimestamp(creation_time)
                if time_init is not None:
                    time_limit = time_limit.replace(
                        hour=time_init.hour,
                        minute=time_init.minute,
                        second=time_init.second,
                        microsecond=time_init.microsecond,
                    )
                if time_limit <= start_time:
                    time_limit = step_forward(time_limit)

            def rotation_function(message, file):
                nonlocal time_limit
                record_time = message.record["time"].replace(tzinfo=None)
                if record_time >= time_limit:
                    while time_limit <= record_time:
                        time_limit = step_forward(time_limit)
                    return True
                return False

            return rotation_function, init_time_rotation

        if rotation is None:
            return None, None
        elif isinstance(rotation, str):
            size = string_parsers.parse_size(rotation)
            if size is not None:
                return self._make_rotation_function(size)
            interval = string_parsers.parse_duration(rotation)
            if interval is not None:
                return self._make_rotation_function(interval)
            frequency = string_parsers.parse_frequency(rotation)
            if frequency is not None:
                return make_from_time(frequency)
            daytime = string_parsers.parse_daytime(rotation)
            if daytime is not None:
                day, time = daytime
                if day is None:
                    return self._make_rotation_function(time)
                if time is None:
                    time = datetime_.time(0, 0, 0)

                def next_day(t):
                    while True:
                        t += datetime_.timedelta(days=1)
                        if t.weekday() == day:
                            return t

                return make_from_time(next_day, time_init=time)
            raise ValueError("Cannot parse rotation from: '%s'" % rotation)
        elif isinstance(rotation, (numbers.Real, decimal.Decimal)):
            return make_from_size(rotation)
        elif isinstance(rotation, datetime_.time):

            def next_day(t):
                return t + datetime_.timedelta(days=1)

            return make_from_time(next_day, time_init=rotation)
        elif isinstance(rotation, datetime_.timedelta):

            def add_interval(t):
                return t + rotation

            return make_from_time(add_interval)
        elif callable(rotation):
            return rotation, None
        else:
            raise ValueError(
                "Cannot infer rotation for objects of type: '%s'" % type(rotation).__name__
            )

    def _make_retention_function(self, retention):
        def make_from_filter(filter_logs):
            def retention_function(logs):
                for log in filter_logs(logs):
                    os.remove(log)

            return retention_function

        if retention is None:
            return None
        elif isinstance(retention, str):
            interval = string_parsers.parse_duration(retention)
            if interval is None:
                raise ValueError("Cannot parse retention from: '%s'" % retention)
            return self._make_retention_function(interval)
        elif isinstance(retention, int):

            def key_log(log):
                return (-os.stat(log).st_mtime, log)

            def filter_logs(logs):
                return sorted(logs, key=key_log)[retention:]

            return make_from_filter(filter_logs)
        elif isinstance(retention, datetime_.timedelta):
            seconds = retention.total_seconds()

            def filter_logs(logs):
                t = datetime.now().timestamp()
                return [log for log in logs if os.stat(log).st_mtime <= t - seconds]

            return make_from_filter(filter_logs)
        elif callable(retention):
            return retention
        else:
            raise ValueError(
                "Cannot infer retention for objects of type: '%s'" % type(retention).__name__
            )

    def _make_compression_function(self, compression):
        def make_compress_generic(opener, **kwargs):
            def compress(path_in, path_out):
                with open(path_in, "rb") as f_in:
                    with opener(path_out, "wb", **kwargs) as f_out:
                        shutil.copyfileobj(f_in, f_out)

            return compress

        def make_compress_archive(mode):
            import tarfile

            def compress(path_in, path_out):
                with tarfile.open(path_out, "w:" + mode) as f_comp:
                    f_comp.add(path_in, os.path.basename(path_in))

            return compress

        def make_compress_zipped():
            import zipfile

            def compress(path_in, path_out):
                with zipfile.ZipFile(path_out, "w", compression=zipfile.ZIP_DEFLATED) as f_comp:
                    f_comp.write(path_in, os.path.basename(path_in))

            return compress

        if compression is None:
            return None
        elif isinstance(compression, str):
            ext = compression.strip().lstrip(".")

            if ext == "gz":
                import gzip

                compress = make_compress_generic(gzip.open)
            elif ext == "bz2":
                import bz2

                compress = make_compress_generic(bz2.open)
            elif ext == "xz":
                import lzma

                compress = make_compress_generic(lzma.open, format=lzma.FORMAT_XZ)
            elif ext == "lzma":
                import lzma

                compress = make_compress_generic(lzma.open, format=lzma.FORMAT_ALONE)
            elif ext == "tar":
                compress = make_compress_archive("")
            elif ext == "tar.gz":
                import gzip

                compress = make_compress_archive("gz")
            elif ext == "tar.bz2":
                import bz2

                compress = make_compress_archive("bz2")
            elif ext == "tar.xz":
                import lzma

                compress = make_compress_archive("xz")
            elif ext == "zip":
                compress = make_compress_zipped()
            else:
                raise ValueError("Invalid compression format: '%s'" % ext)

            def compression_function(path_in):
                path_out = "{}.{}".format(path_in, ext)
                if os.path.isfile(path_out):
                    creation_time = self._get_creation_time(path_out)
                    creation_datetime = datetime.fromtimestamp(creation_time)
                    date = FileDateFormatter(creation_datetime)
                    root, ext_before = os.path.splitext(path_in)
                    renamed_path = "{}.{}{}.{}".format(root, date, ext_before, ext)
                    os.rename(path_out, renamed_path)
                compress(path_in, path_out)
                os.remove(path_in)

            return compression_function
        elif callable(compression):
            return compression
        else:
            raise ValueError(
                "Cannot infer compression for objects of type: '%s'" % type(compression).__name__
            )

    def stop(self):
        self._terminate(teardown=self._rotation_function is None)

    def _terminate(self, *, teardown):
        if self._file is not None:
            self._file.close()

        if teardown:
            if self._compression_function is not None and self._file_path is not None:
                self._compression_function(self._file_path)

            if self._retention_function is not None:
                logs = glob.glob(self._glob_pattern)
                self._retention_function(logs)

        self._file = None
        self._file_path = None
