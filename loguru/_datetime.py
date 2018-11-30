import re
from calendar import day_abbr, day_name, month_abbr, month_name
from datetime import datetime as datetime_
from datetime import timedelta, timezone
from time import localtime, time

tokens = r"H{1,2}|h{1,2}|m{1,2}|s{1,2}|S{1,6}|YYYY|YY|M{1,4}|D{1,4}|Z{1,2}|zz|A|X|x|E|Q|dddd|ddd|d"

pattern = re.compile(r"(?:{0})|\[(?:{0})\]".format(tokens))


class datetime(datetime_):
    def __format__(self, spec):
        if not spec:
            spec = "%Y-%m-%dT%H:%M:%S.%f%z"

        if "%" in spec:
            return super().__format__(spec)

        year, month, day, hour, minute, second, weekday, yearday, _ = self.timetuple()
        microsecond = self.microsecond
        timestamp = self.timestamp()
        tzinfo = self.tzinfo or timezone(timedelta(seconds=0))
        offset = tzinfo.utcoffset(self).total_seconds()
        sign = ("-", "+")[offset >= 0]
        h, m = divmod(abs(offset // 60), 60)

        rep = {
            "YYYY": "%04d" % year,
            "YY": "%02d" % (year % 100),
            "Q": "%d" % ((month - 1) // 3 + 1),
            "MMMM": month_name[month - 1],
            "MMM": month_abbr[month - 1],
            "MM": "%02d" % month,
            "M": "%d" % month,
            "DDDD": "%03d" % yearday,
            "DDD": "%d" % yearday,
            "DD": "%02d" % day,
            "D": "%d" % day,
            "dddd": day_name[weekday],
            "ddd": day_abbr[weekday],
            "d": "%d" % weekday,
            "E": "%d" % (weekday + 1),
            "HH": "%02d" % hour,
            "H": "%d" % hour,
            "hh": "%02d" % ((hour - 1) % 12 + 1),
            "h": "%d" % ((hour - 1) % 12 + 1),
            "mm": "%02d" % minute,
            "m": "%d" % minute,
            "ss": "%02d" % second,
            "s": "%d" % second,
            "S": "%d" % (microsecond // 100000),
            "SS": "%02d" % (microsecond // 10000),
            "SSS": "%03d" % (microsecond // 1000),
            "SSSS": "%04d" % (microsecond // 100),
            "SSSSS": "%05d" % (microsecond // 10),
            "SSSSSS": "%06d" % microsecond,
            "A": ("AM", "PM")[hour // 12],
            "Z": "%s%02d:%02d" % (sign, h, m),
            "ZZ": "%s%02d%02d" % (sign, h, m),
            "zz": tzinfo.tzname(self) or "",
            "X": "%d" % timestamp,
            "x": "%d" % (int(timestamp) * 1000000 + microsecond),
        }

        def get(m):
            try:
                return rep[m[0]]
            except KeyError:
                return m[0][1:-1]

        return pattern.sub(get, spec)


def now():
    now = datetime.now()
    local = localtime(now.timestamp())
    tzinfo = timezone(timedelta(seconds=local.tm_gmtoff), local.tm_zone)
    return now.replace(tzinfo=tzinfo)
