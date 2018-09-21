import datetime
import re

import pendulum


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

    return pendulum.Duration(seconds=seconds)


def parse_frequency(frequency):
    frequency = frequency.strip().lower()

    if frequency == 'hourly':
        def hourly(t):
            return t.add(hours=1).start_of('hour')
        return hourly
    elif frequency == 'daily':
        def daily(t):
            return t.add(days=1).start_of('day')
        return daily
    elif frequency == 'weekly':
        def weekly(t):
            return t.add(weeks=1).start_of('week')
        return weekly
    elif frequency == 'monthly':
        def monthly(t):
            return t.add(months=1).start_of('month')
        return monthly
    elif frequency == 'yearly':
        def yearly(t):
            return t.add(years=1).start_of('year')
        return yearly

    return None


def parse_daytime(daytime):
    daytime = daytime.strip()

    daytime_reg = re.compile(r'^(.*?)\s+at\s+(.*)$', flags=re.I)
    day_reg = re.compile(r'^w\d+$', flags=re.I)
    time_reg = re.compile(r'^[\d\.\:\,]+(?:\s*[ap]m)?$', flags=re.I)

    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    pdays = [getattr(pendulum, day.upper()) for day in days]

    daytime_match = daytime_reg.match(daytime)
    if daytime_match:
        day, time = daytime_match.groups()
    elif time_reg.match(daytime):
        day, time = None, daytime
    elif day_reg.match(daytime) or daytime.lower() in days:
        day, time = daytime, None
    else:
        return None

    if day is not None:
        day_ = day.lower()
        if day_reg.match(day):
            d = int(day[1:])
            if not 0 <= d < len(days):
                raise ValueError("Invalid weekday index while parsing daytime: '%d'" % d)
            day = pdays[d]
        elif day_ in days:
            day = pdays[days.index(day_)]
        else:
            raise ValueError("Invalid weekday value while parsing daytime: '%s'" % day)

    if time is not None:
        time_ = time
        try:
            time = pendulum.parse(time, exact=True, strict=False)
        except Exception as e:
            raise ValueError("Invalid time while parsing daytime: '%s'" % time) from e
        else:
            if not isinstance(time, datetime.time):
                raise ValueError("Cannot strictly parse time from: '%s'" % time_)

    return day, time
