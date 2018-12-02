import datetime
import decimal
import glob
import locale
import numbers
import os
import shutil
import string

from . import _string_parsers as string_parsers
from ._datetime import now


class FileDateFormatter:
    def __init__(self):
        self.datetime = now()

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
        self.mode = mode
        self.buffering = buffering
        self.encoding = encoding or locale.getpreferredencoding(False)
        self.kwargs = kwargs.copy()
        self.path = str(path)

        self.rotation_function = self.make_rotation_function(rotation)
        self.retention_function = self.make_retention_function(retention)
        self.compression_function = self.make_compression_function(compression)
        self.glob_pattern = self.make_glob_pattern(self.path)

        self.file = None
        self.file_path = None
        self.write = None
        self.file_write = None

        if delay:
            self.write = self.delayed_write
        else:
            self.initialize_file(rename_existing=False)
            self.setup_write_function()

    def setup_write_function(self):
        self.file_write = self.file.write

        if self.rotation_function is None:
            self.write = self.file_write
        else:
            self.write = self.rotating_write

    def delayed_write(self, message):
        self.initialize_file(rename_existing=False)
        self.setup_write_function()
        self.write(message)

    def rotating_write(self, message):
        if self.rotation_function(message, self.file):
            self.terminate(teardown=True)
            self.initialize_file(rename_existing=True)
            self.setup_write_function()
        self.file_write(message)

    def initialize_file(self, *, rename_existing):
        new_path = self.format_path()
        new_dir = os.path.dirname(new_path)
        os.makedirs(new_dir, exist_ok=True)

        if rename_existing and os.path.isfile(new_path):
            root, ext = os.path.splitext(new_path)
            renamed_path = "{}.{}{}".format(root, FileDateFormatter(), ext)
            os.rename(new_path, renamed_path)

        self.file_path = new_path
        self.file = open(
            new_path,
            mode=self.mode,
            buffering=self.buffering,
            encoding=self.encoding,
            **self.kwargs
        )

    def format_path(self):
        path = self.path.format_map({"time": FileDateFormatter()})
        return os.path.abspath(path)

    @staticmethod
    def make_glob_pattern(path):
        tokens = string.Formatter().parse(path)
        parts = (glob.escape(text) + "*" * (name is not None) for text, name, *_ in tokens)
        root, ext = os.path.splitext("".join(parts))
        if ext:
            pattern = root + ".*"
        else:
            pattern = root + "*"
        return pattern

    def make_rotation_function(self, rotation):
        def make_from_size(size_limit):
            def rotation_function(message, file):
                file.seek(0, 2)
                return file.tell() + len(message) >= size_limit

            return rotation_function

        def make_from_time(step_forward, time_init=None):
            start_time = time_limit = now().replace(tzinfo=None)
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

            return rotation_function

        if rotation is None:
            return None
        elif isinstance(rotation, str):
            size = string_parsers.parse_size(rotation)
            if size is not None:
                return self.make_rotation_function(size)
            interval = string_parsers.parse_duration(rotation)
            if interval is not None:
                return self.make_rotation_function(interval)
            frequency = string_parsers.parse_frequency(rotation)
            if frequency is not None:
                return make_from_time(frequency)
            daytime = string_parsers.parse_daytime(rotation)
            if daytime is not None:
                day, time = daytime
                if day is None:
                    return self.make_rotation_function(time)
                if time is None:
                    time = datetime.time(0, 0, 0)

                def next_day(t):
                    while True:
                        t += datetime.timedelta(days=1)
                        if t.weekday() == day:
                            return t

                return make_from_time(next_day, time_init=time)
            raise ValueError("Cannot parse rotation from: '%s'" % rotation)
        elif isinstance(rotation, (numbers.Real, decimal.Decimal)):
            return make_from_size(rotation)
        elif isinstance(rotation, datetime.time):

            def next_day(t):
                return t + datetime.timedelta(days=1)

            return make_from_time(next_day, time_init=rotation)
        elif isinstance(rotation, datetime.timedelta):

            def add_interval(t):
                return t + rotation

            return make_from_time(add_interval)
        elif callable(rotation):
            return rotation
        else:
            raise ValueError(
                "Cannot infer rotation for objects of type: '%s'" % type(rotation).__name__
            )

    def make_retention_function(self, retention):
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
            return self.make_retention_function(interval)
        elif isinstance(retention, int):

            def key_log(log):
                return (-os.stat(log).st_mtime, log)

            def filter_logs(logs):
                return sorted(logs, key=key_log)[retention:]

            return make_from_filter(filter_logs)
        elif isinstance(retention, datetime.timedelta):
            seconds = retention.total_seconds()

            def filter_logs(logs):
                t = now().timestamp()
                return [log for log in logs if os.stat(log).st_mtime <= t - seconds]

            return make_from_filter(filter_logs)
        elif callable(retention):
            return retention
        else:
            raise ValueError(
                "Cannot infer retention for objects of type: '%s'" % type(retention).__name__
            )

    def make_compression_function(self, compression):
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
                    root, ext_before = os.path.splitext(path_in)
                    renamed_template = "{}.{}{}.{}"
                    date = FileDateFormatter()
                    renamed_path = renamed_template.format(root, date, ext_before, ext)
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
        self.terminate(teardown=self.rotation_function is None)

    def terminate(self, *, teardown):
        if self.file is not None:
            self.file.close()

        if teardown:
            if self.compression_function is not None and self.file_path is not None:
                self.compression_function(self.file_path)

            if self.retention_function is not None:
                logs = glob.glob(self.glob_pattern)
                self.retention_function(logs)

        self.file = None
        self.file_path = None
