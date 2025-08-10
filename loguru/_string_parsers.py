import datetime
import re
from typing import Optional, Tuple


class Frequencies:
    """Provide static methods to compute the next occurrence of various time frequencies.

    Includes hourly, daily, weekly, monthly, and yearly frequencies
    based on a given datetime object.
    """

    @staticmethod
    def hourly(t: datetime.datetime) -> datetime.datetime:
        """Compute the next hour occurrence.

        Parameters
        ----------
        t : datetime.datetime
            The reference datetime.

        Returns
        -------
        datetime.datetime
            Next hour with minutes, seconds, microseconds set to zero.
        """
        dt = t + datetime.timedelta(hours=1)
        return dt.replace(minute=0, second=0, microsecond=0)

    @staticmethod
    def daily(t: datetime.datetime) -> datetime.datetime:
        """Compute the next day occurrence.

        Parameters
        ----------
        t : datetime.datetime
            The reference datetime.

        Returns
        -------
        datetime.datetime
            Next day with hour, minutes, seconds, microseconds set to zero.
        """
        dt = t + datetime.timedelta(days=1)
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)

    @staticmethod
    def weekly(t: datetime.datetime) -> datetime.datetime:
        """Compute the next week occurrence.

        Parameters
        ----------
        t : datetime.datetime
            The reference datetime.

        Returns
        -------
        datetime.datetime
            Next Monday with hour, minutes, seconds, microseconds set to zero.
        """
        dt = t + datetime.timedelta(days=7 - t.weekday())
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)

    @staticmethod
    def monthly(t: datetime.datetime) -> datetime.datetime:
        """Compute the next month occurrence.

        Parameters
        ----------
        t : datetime.datetime
            The reference datetime.

        Returns
        -------
        datetime.datetime
            First day of next month with hour, minutes, seconds, microseconds set to zero.
        """
        if t.month == 12:
            y, m = t.year + 1, 1
        else:
            y, m = t.year, t.month + 1
        return t.replace(year=y, month=m, day=1, hour=0, minute=0, second=0, microsecond=0)

    @staticmethod
    def yearly(t: datetime.datetime) -> datetime.datetime:
        """Compute the next year occurrence.

        Parameters
        ----------
        t : datetime.datetime
            The reference datetime.

        Returns
        -------
        datetime.datetime
            First day of next year with hour, minutes, seconds, microseconds set to zero.
        """
        y = t.year + 1
        return t.replace(year=y, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)


def parse_size(size: str) -> Optional[float]:
    """Parse a size string with optional units into bits.

    Supports formats like '100MB', '2GiB', '1.5TB'. Case insensitive.

    Parameters
    ----------
    size : str
        Size string to parse (e.g., '100MB', '2GiB').

    Returns
    -------
    float | None
        Size in bits or None if invalid format.

    Raises
    ------
    ValueError
        If numeric value or unit is invalid.
    """
    size = size.strip()
    reg = re.compile(r"([e\+\-\.\d]+)\s*([kmgtpezy])?(i)?(b)", flags=re.I)

    match = reg.fullmatch(size)

    if not match:
        return None

    s, u, i, b = match.groups()

    try:
        s = float(s)
    except ValueError as err:
        raise ValueError("Invalid float value while parsing size: '%s'" % s) from err

    u = "kmgtpezy".index(u.lower()) + 1 if u else 0
    i = 1024 if i else 1000
    b = {"b": 8, "B": 1}[b] if b else 1
    return s * i**u / b


def parse_duration(duration: str) -> Optional[datetime.timedelta]:
    """Parse a duration string and return a corresponding timedelta object.

    The string can include multiple units (years, months, weeks, days, hours, minutes, seconds).
    Example: "1h 30min", "2 days, 3h", "1.5y 2months".

    Parameters
    ----------
    duration : str
        The duration string to parse.

    Returns
    -------
    datetime.timedelta | None
        The parsed duration or None if input is invalid.

    Raises
    ------
    ValueError
        If a value cannot be converted to float or if an invalid unit is encountered.
    """
    duration = duration.strip()
    reg = r"(?:([e\+\-\.\d]+)\s*([a-z]+)[\s\,]*)"

    units = [
        ("y|years?", 31536000),
        ("months?", 2628000),
        ("w|weeks?", 604800),
        ("d|days?", 86400),
        ("h|hours?", 3600),
        ("min(?:ute)?s?", 60),
        ("s|sec(?:ond)?s?", 1),  # spellchecker: disable-line
        ("ms|milliseconds?", 0.001),
        ("us|microseconds?", 0.000001),
    ]

    if not re.fullmatch(reg + "+", duration, flags=re.I):
        return None

    seconds = 0

    for value, unit in re.findall(reg, duration, flags=re.I):
        try:
            value = float(value)
        except ValueError as e:
            raise ValueError("Invalid float value while parsing duration: '%s'" % value) from e

        try:
            unit = next(u for r, u in units if re.fullmatch(r, unit, flags=re.I))
        except StopIteration:
            raise ValueError("Invalid unit value while parsing duration: '%s'" % unit) from None

        seconds += value * unit

    return datetime.timedelta(seconds=seconds)


def parse_frequency(frequency: str):
    """Parse a frequency string and return the corresponding Frequencies method.

    Supported frequencies: hourly, daily, weekly, monthly, yearly.

    Parameters
    ----------
    frequency : str
        The frequency string.

    Returns
    -------
    Callable | None
        Corresponding Frequencies method or None if unrecognized.
    """
    frequencies = {
        "hourly": Frequencies.hourly,
        "daily": Frequencies.daily,
        "weekly": Frequencies.weekly,
        "monthly": Frequencies.monthly,
        "yearly": Frequencies.yearly,
    }
    frequency = frequency.strip().lower()
    return frequencies.get(frequency, None)


def parse_day(day: str) -> Optional[int]:
    """Parse a weekday string and return its integer value.

    Accepts full day names or "w0" to "w6".

    Parameters
    ----------
    day : str
        The day to parse.

    Returns
    -------
    int | None
        Integer value (Monday=0 ... Sunday=6), or None if invalid.

    Raises
    ------
    ValueError
        If the digit in 'wX' is not in range [0-6].
    """
    days = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }
    day = day.strip().lower()
    if day in days:
        return days[day]
    if day.startswith("w") and day[1:].isdigit():
        day = int(day[1:])
        if not 0 <= day < 7:
            raise ValueError("Invalid weekday value while parsing day (expected [0-6]): '%d'" % day)
    else:
        day = None

    return day


def parse_time(time: str) -> datetime.time:
    """Parse a time string and return a `datetime.time` object.

    Supports formats: HH, HH:MM, HH:MM:SS, HH AM/PM, etc.

    Parameters
    ----------
    time : str
        The time string.

    Returns
    -------
    datetime.time
        The parsed time.

    Raises
    ------
    ValueError
        If input doesn't match any supported format.
    """
    time = time.strip()
    reg = re.compile(r"^[\d\.\:]+\s*(?:[ap]m)?$", flags=re.I)

    if not reg.match(time):
        return None

    formats = [
        "%H",
        "%H:%M",
        "%H:%M:%S",
        "%H:%M:%S.%f",
        "%I %p",
        "%I:%M %S",
        "%I:%M:%S %p",
        "%I:%M:%S.%f %p",
    ]

    for format_ in formats:
        try:
            dt = datetime.datetime.strptime(time, format_)
        except ValueError:
            pass
        else:
            return dt.time()

    raise ValueError("Unrecognized format while parsing time: '%s'" % time)


def parse_daytime(daytime: str) -> Optional[Tuple[int, datetime.time]]:
    """Parse a string representing a day and time separated by 'at'.

    Parameters
    ----------
    daytime : str
        The day and time string.

    Returns
    -------
    tuple[int, datetime.time] | None
        Parsed (day, time) or None.

    Raises
    ------
    ValueError
        If the day or time cannot be parsed.
    """
    daytime = daytime.strip()
    reg = re.compile(r"^(.*?)\s+at\s+(.*)$", flags=re.I)

    match = reg.match(daytime)
    if match:
        day, time = match.groups()
    else:
        day = time = daytime

    try:
        parsed_day = parse_day(day)
        if match and parsed_day is None:
            raise ValueError("Unparsable day")
    except ValueError as e:
        raise ValueError("Invalid day while parsing daytime: '%s'" % day) from e

    try:
        parsed_time = parse_time(time)
        if match and parsed_time is None:
            raise ValueError("Unparsable time")
    except ValueError as e:
        raise ValueError("Invalid time while parsing daytime: '%s'" % time) from e

    if parsed_day is None and parsed_time is None:
        return None

    return parsed_day, parsed_time
