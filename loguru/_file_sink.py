import datetime as datetime_
import decimal
import glob
import locale
import numbers
import os
import shutil
import string
from functools import partial

from . import _string_parsers as string_parsers
from ._ctime_functions import get_ctime, set_ctime
from ._datetime import aware_now, datetime


def generate_rename_path(root, ext, creation_time):
    creation_datetime = datetime.fromtimestamp(creation_time)
    date = FileDateFormatter(creation_datetime)

    renamed_path = "{}.{}{}".format(root, date, ext)
    counter = 1

    while os.path.exists(renamed_path):
        counter += 1
        renamed_path = "{}.{}.{}{}".format(root, date, counter, ext)

    return renamed_path


class FileDateFormatter:
    def __init__(self, datetime=None):
        self.datetime = datetime or aware_now()

    def __format__(self, spec):
        if not spec:
            spec = "%Y-%m-%d_%H-%M-%S_%f"
        return self.datetime.__format__(spec)


class Compression:
    @staticmethod
    def add_compress(path_in, path_out, opener, **kwargs):
        with opener(path_out, **kwargs) as f_comp:
            f_comp.add(path_in, os.path.basename(path_in))

    @staticmethod
    def write_compress(path_in, path_out, opener, **kwargs):
        with opener(path_out, **kwargs) as f_comp:
            f_comp.write(path_in, os.path.basename(path_in))

    @staticmethod
    def copy_compress(path_in, path_out, opener, **kwargs):
        with open(path_in, "rb") as f_in:
            with opener(path_out, **kwargs) as f_out:
                shutil.copyfileobj(f_in, f_out)

    @staticmethod
    def compression(path_in, ext, compress_function):
        path_out = "{}{}".format(path_in, ext)

        if os.path.exists(path_out):
            creation_time = get_ctime(path_out)
            root, ext_before = os.path.splitext(path_in)
            renamed_path = generate_rename_path(root, ext_before + ext, creation_time)
            os.rename(path_out, renamed_path)
        compress_function(path_in, path_out)
        os.remove(path_in)


class Retention:
    @staticmethod
    def retention_count(logs, number):
        def key_log(log):
            return (-os.stat(log).st_mtime, log)

        for log in sorted(logs, key=key_log)[number:]:
            os.remove(log)

    @staticmethod
    def retention_age(logs, seconds):
        t = datetime.now().timestamp()
        for log in logs:
            if os.stat(log).st_mtime <= t - seconds:
                os.remove(log)


class Rotation:
    @staticmethod
    def forward_day(t):
        return t + datetime_.timedelta(days=1)

    @staticmethod
    def forward_weekday(t, weekday):
        while True:
            t += datetime_.timedelta(days=1)
            if t.weekday() == weekday:
                return t

    @staticmethod
    def forward_interval(t, interval):
        return t + interval

    @staticmethod
    def rotation_size(message, file, size_limit):
        file.seek(0, 2)
        return file.tell() + len(message) > size_limit

    class RotationTime:
        def __init__(self, step_forward, time_init=None):
            self._step_forward = step_forward
            self._time_init = time_init
            self._limit = None

        def __call__(self, message, file):
            if self._limit is None:
                filepath = os.path.realpath(file.name)
                creation_time = get_ctime(filepath)
                set_ctime(filepath, creation_time)
                start_time = limit = datetime.fromtimestamp(creation_time)
                if self._time_init is not None:
                    limit = limit.replace(
                        hour=self._time_init.hour,
                        minute=self._time_init.minute,
                        second=self._time_init.second,
                        microsecond=self._time_init.microsecond,
                    )
                if limit <= start_time:
                    limit = self._step_forward(limit)
                self._limit = limit

            record_time = message.record["time"].replace(tzinfo=None)
            if record_time >= self._limit:
                while self._limit <= record_time:
                    self._limit = self._step_forward(self._limit)
                return True
            return False


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

        self._kwargs = {**kwargs, "mode": mode, "buffering": buffering, "encoding": self.encoding}
        self._path = str(path)

        self._glob_patterns = self._make_glob_patterns(self._path)
        self._rotation_function = self._make_rotation_function(rotation)
        self._retention_function = self._make_retention_function(retention)
        self._compression_function = self._make_compression_function(compression)

        self._file = None
        self._file_path = None

        if not delay:
            self._initialize_file()

    def write(self, message):
        if self._file is None:
            self._initialize_file()

        if self._rotation_function is not None and self._rotation_function(message, self._file):
            self._terminate_file(is_rotating=True)

        self._file.write(message)

    def _prepare_new_path(self):
        path = self._path.format_map({"time": FileDateFormatter()})
        path = os.path.abspath(path)
        dirname = os.path.dirname(path)
        os.makedirs(dirname, exist_ok=True)
        return path

    def _initialize_file(self):
        path = self._prepare_new_path()
        self._file = open(path, **self._kwargs)
        self._file_path = path

    def _terminate_file(self, *, is_rotating=False):
        old_path = self._file_path

        if self._file is not None:
            self._file.close()
            self._file = None
            self._file_path = None

        if is_rotating:
            new_path = self._prepare_new_path()

            if new_path == old_path:
                creation_time = get_ctime(old_path)
                root, ext = os.path.splitext(old_path)
                renamed_path = generate_rename_path(root, ext, creation_time)
                os.rename(old_path, renamed_path)
                old_path = renamed_path

        if is_rotating or self._rotation_function is None:
            if self._compression_function is not None and old_path is not None:
                self._compression_function(old_path)

            if self._retention_function is not None:
                logs = {
                    file
                    for pattern in self._glob_patterns
                    for file in glob.glob(pattern)
                    if os.path.isfile(file)
                }
                self._retention_function(list(logs))

        if is_rotating:
            file = open(new_path, **self._kwargs)
            set_ctime(new_path, datetime.now().timestamp())

            self._file_path = new_path
            self._file = file

    def stop(self):
        self._terminate_file(is_rotating=False)

    async def complete(self):
        pass

    @staticmethod
    def _make_glob_patterns(path):
        formatter = string.Formatter()
        tokens = formatter.parse(path)
        escaped = "".join(glob.escape(text) + "*" * (name is not None) for text, name, *_ in tokens)

        root, ext = os.path.splitext(escaped)

        if not ext:
            return [escaped, escaped + ".*"]

        return [escaped, escaped + ".*", root + ".*" + ext, root + ".*" + ext + ".*"]

    @staticmethod
    def _make_rotation_function(rotation):
        if rotation is None:
            return None
        elif isinstance(rotation, str):
            size = string_parsers.parse_size(rotation)
            if size is not None:
                return FileSink._make_rotation_function(size)
            interval = string_parsers.parse_duration(rotation)
            if interval is not None:
                return FileSink._make_rotation_function(interval)
            frequency = string_parsers.parse_frequency(rotation)
            if frequency is not None:
                return Rotation.RotationTime(frequency)
            daytime = string_parsers.parse_daytime(rotation)
            if daytime is not None:
                day, time = daytime
                if day is None:
                    return FileSink._make_rotation_function(time)
                if time is None:
                    time = datetime_.time(0, 0, 0)
                step_forward = partial(Rotation.forward_weekday, weekday=day)
                return Rotation.RotationTime(step_forward, time)
            raise ValueError("Cannot parse rotation from: '%s'" % rotation)
        elif isinstance(rotation, (numbers.Real, decimal.Decimal)):
            return partial(Rotation.rotation_size, size_limit=rotation)
        elif isinstance(rotation, datetime_.time):
            return Rotation.RotationTime(Rotation.forward_day, rotation)
        elif isinstance(rotation, datetime_.timedelta):
            step_forward = partial(Rotation.forward_interval, interval=rotation)
            return Rotation.RotationTime(step_forward)
        elif callable(rotation):
            return rotation
        else:
            raise TypeError(
                "Cannot infer rotation for objects of type: '%s'" % type(rotation).__name__
            )

    @staticmethod
    def _make_retention_function(retention):
        if retention is None:
            return None
        elif isinstance(retention, str):
            interval = string_parsers.parse_duration(retention)
            if interval is None:
                raise ValueError("Cannot parse retention from: '%s'" % retention)
            return FileSink._make_retention_function(interval)
        elif isinstance(retention, int):
            return partial(Retention.retention_count, number=retention)
        elif isinstance(retention, datetime_.timedelta):
            return partial(Retention.retention_age, seconds=retention.total_seconds())
        elif callable(retention):
            return retention
        else:
            raise TypeError(
                "Cannot infer retention for objects of type: '%s'" % type(retention).__name__
            )

    @staticmethod
    def _make_compression_function(compression):
        if compression is None:
            return None
        elif isinstance(compression, str):
            ext = compression.strip().lstrip(".")

            if ext == "gz":
                import gzip

                compress = partial(Compression.copy_compress, opener=gzip.open, mode="wb")
            elif ext == "bz2":
                import bz2

                compress = partial(Compression.copy_compress, opener=bz2.open, mode="wb")

            elif ext == "xz":
                import lzma

                compress = partial(
                    Compression.copy_compress, opener=lzma.open, mode="wb", format=lzma.FORMAT_XZ
                )

            elif ext == "lzma":
                import lzma

                compress = partial(
                    Compression.copy_compress, opener=lzma.open, mode="wb", format=lzma.FORMAT_ALONE
                )
            elif ext == "tar":
                import tarfile

                compress = partial(Compression.add_compress, opener=tarfile.open, mode="w:")
            elif ext == "tar.gz":
                import gzip
                import tarfile

                compress = partial(Compression.add_compress, opener=tarfile.open, mode="w:gz")
            elif ext == "tar.bz2":
                import bz2
                import tarfile

                compress = partial(Compression.add_compress, opener=tarfile.open, mode="w:bz2")

            elif ext == "tar.xz":
                import lzma
                import tarfile

                compress = partial(Compression.add_compress, opener=tarfile.open, mode="w:xz")
            elif ext == "zip":
                import zipfile

                compress = partial(
                    Compression.write_compress,
                    opener=zipfile.ZipFile,
                    mode="w",
                    compression=zipfile.ZIP_DEFLATED,
                )
            else:
                raise ValueError("Invalid compression format: '%s'" % ext)

            return partial(Compression.compression, ext="." + ext, compress_function=compress)
        elif callable(compression):
            return compression
        else:
            raise TypeError(
                "Cannot infer compression for objects of type: '%s'" % type(compression).__name__
            )
