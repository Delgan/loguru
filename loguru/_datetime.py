import functools
import re
from calendar import day_abbr, day_name, month_abbr, month_name
from datetime import datetime as datetime_
from datetime import timedelta, timezone
from time import localtime, strftime
from typing import Callable

tokens = r"H{1,2}|h{1,2}|m{1,2}|s{1,2}|S+|YYYY|YY|M{1,4}|D{1,4}|Z{1,2}|zz|A|X|x|E|Q|dddd|ddd|d"

pattern = re.compile(r"(?:{0})|\[(?:{0}|!UTC|)\]".format(tokens))


def __default_fmt_fast_path(dt: datetime_) -> str:
    return (
        f"{dt.year:04d}-{dt.month:02d}-{dt.day:02d}"
        f" {dt.hour:02d}:{dt.month:02d}:{dt.day:02d}.{dt.microsecond // 1000:03d}"
    )


@functools.lru_cache(maxsize=None)
def _compile_format(spec: str) -> Callable[[datetime_], str]:
    # default format for text output
    if spec == "YYYY-MM-DD HH:mm:ss.SSS":
        return __default_fmt_fast_path

    if spec.endswith("!UTC"):
        use_utc: bool = True
        spec = spec[:-4]
    else:
        use_utc: bool = False

    if not spec:
        spec = "%Y-%m-%dT%H:%M:%S.%f%z"

    if "%" in spec:

        def compiled(dt: datetime_) -> str:
            if use_utc:
                dt = dt.astimezone(timezone.utc)

            return datetime_.__format__(dt, spec)

        return compiled

    if "SSSSSSS" in spec:
        raise ValueError(
            "Invalid time format: the provided format string contains more than six successive "
            "'S' characters. This may be due to an attempt to use nanosecond precision, which "
            "is not supported."
        )

    def compiled(dt: datetime_) -> str:
        if use_utc:
            dt = dt.astimezone(timezone.utc)

        def repl(m: re.Match[str]) -> str:
            fmt = m.group(0)
            if fmt == "YYYY":
                return f"{dt.year:04d}"
            if fmt == "YY":
                return f"{dt.year % 100:02d}"

            if fmt == "Q":
                return "%d" % ((dt.month - 1) // 3 + 1)

            if fmt == "MMMM":
                return month_name[dt.month]
            if fmt == "MMM":
                return month_abbr[dt.month]
            if fmt == "MM":
                return f"{dt.month:02d}"
            if fmt == "M":
                return f"{dt.month:d}"

            if fmt == "DDDD":
                return "%03d" % dt.timetuple().tm_yday
            if fmt == "DDD":
                return "%d" % dt.timetuple().tm_yday
            if fmt == "DD":
                return "%02d" % dt.day
            if fmt == "D":
                return "%d" % dt.day

            if fmt == "dddd":
                return day_name[dt.weekday()]
            if fmt == "ddd":
                return day_abbr[dt.weekday()]
            if fmt == "d":
                return "%d" % dt.weekday()

            if fmt == "E":
                return f"{dt.weekday() + 1:d}"

            if fmt == "HH":
                return "%02d" % dt.hour
            if fmt == "H":
                return "%d" % dt.hour
            if fmt == "hh":
                return "%02d" % ((dt.hour - 1) % 12 + 1)
            if fmt == "h":
                return "%d" % ((dt.hour - 1) % 12 + 1)

            if fmt == "mm":
                return "%02d" % dt.minute
            if fmt == "m":
                return "%d" % dt.minute
            if fmt == "ss":
                return "%02d" % dt.second
            if fmt == "s":
                return "%d" % dt.second
            if fmt == "S":
                return "%d" % (dt.microsecond // 100000)
            if fmt == "SS":
                return "%02d" % (dt.microsecond // 10000)
            if fmt == "SSS":
                return "%03d" % (dt.microsecond // 1000)
            if fmt == "SSSS":
                return "%04d" % (dt.microsecond // 100)
            if fmt == "SSSSS":
                return "%05d" % (dt.microsecond // 10)
            if fmt == "SSSSSS":
                return "%06d" % dt.microsecond

            if fmt == "A":
                return ("AM", "PM")[dt.hour // 12]
            if fmt == "Z":
                tzinfo = dt.tzinfo or timezone(timedelta(seconds=0))
                offset = tzinfo.utcoffset(dt).total_seconds()
                sign = ("-", "+")[offset >= 0]
                (h, m), s = divmod(abs(offset // 60), 60), abs(offset) % 60
                return "%s%02d:%02d%s" % (
                    sign,
                    h,
                    m,
                    (":%09.06f" % s)[: 11 if s % 1 else 3] * (s > 0),
                )
            if fmt == "ZZ":
                tzinfo = dt.tzinfo or timezone(timedelta(seconds=0))
                offset = tzinfo.utcoffset(dt).total_seconds()
                sign = ("-", "+")[offset >= 0]
                (h, m), s = divmod(abs(offset // 60), 60), abs(offset) % 60
                return "%s%02d%02d%s" % (
                    sign,
                    h,
                    m,
                    ("%09.06f" % s)[: 10 if s % 1 else 2] * (s > 0),
                )
            if fmt == "zz":
                tzinfo = dt.tzinfo or timezone(timedelta(seconds=0))
                return tzinfo.tzname(dt) or ""
            if fmt == "X":
                return "%d" % dt.timestamp()
            if fmt == "x":
                return "%d" % (int(dt.timestamp()) * 1000000 + dt.microsecond)

            return fmt[1:-1]

        return pattern.sub(string=spec, repl=repl)

    return compiled


class datetime(datetime_):  # noqa: N801
    def __format__(self, spec):
        fmt = _compile_format(spec)
        return fmt(self)


def aware_now():
    now = datetime_.now()
    timestamp = now.timestamp()
    local = localtime(timestamp)

    try:
        seconds = local.tm_gmtoff
        zone = local.tm_zone
    except AttributeError:
        # Workaround for Python 3.5.
        utc_naive = datetime_.fromtimestamp(timestamp, tz=timezone.utc).replace(tzinfo=None)
        offset = datetime_.fromtimestamp(timestamp) - utc_naive
        seconds = offset.total_seconds()
        zone = strftime("%Z")

    tzinfo = timezone(timedelta(seconds=seconds), zone)

    return datetime.combine(now.date(), now.time().replace(tzinfo=tzinfo))
