import datetime
import re


class Frequencies:
    """
    A utility class providing static methods to compute the next occurrence of various time frequencies
    (hourly, daily, weekly, monthly, yearly) based on a given datetime object.

    Methods
    -------
    hourly(t: datetime.datetime) -> datetime.datetime
        Returns the next hour, with minutes, seconds, and microseconds set to zero.

    daily(t: datetime.datetime) -> datetime.datetime
        Returns the next day, with hour, minutes, seconds, and microseconds set to zero.

    weekly(t: datetime.datetime) -> datetime.datetime
        Returns the next week's start (Monday), with hour, minutes, seconds, and microseconds set to zero.

    monthly(t: datetime.datetime) -> datetime.datetime
        Returns the first day of the next month, with hour, minutes, seconds, and microseconds set to zero.

    yearly(t: datetime.datetime) -> datetime.datetime
        Returns the first day of the next year, with hour, minutes, seconds, and microseconds set to zero.
    """

    @staticmethod
    def hourly(t):
        """Compute the next hour occurrence.

        Args:
            t (datetime.datetime): The reference datetime

        Returns:
            datetime.datetime: Next hour with minutes, seconds, microseconds set to zero
        """
        dt = t + datetime.timedelta(hours=1)
        return dt.replace(minute=0, second=0, microsecond=0)

    @staticmethod
    def daily(t):
        """Compute the next day occurrence.

        Args:
            t (datetime.datetime): The reference datetime

        Returns:
            datetime.datetime: Next day with hour, minutes, seconds, microseconds set to zero
        """
        dt = t + datetime.timedelta(days=1)
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)

    @staticmethod
    def weekly(t):
        """Compute the next week occurrence.

        Args:
            t (datetime.datetime): The reference datetime

        Returns:
            datetime.datetime: Next Monday with hour, minutes, seconds, microseconds set to zero
        """
        dt = t + datetime.timedelta(days=7 - t.weekday())
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)

    @staticmethod
    def monthly(t):
        """Compute the next month occurrence.

        Args:
            t (datetime.datetime): The reference datetime

        Returns:
            datetime.datetime: First day of next month with hour, minutes, seconds, microseconds set to zero
        """
        if t.month == 12:
            y, m = t.year + 1, 1
        else:
            y, m = t.year, t.month + 1
        return t.replace(year=y, month=m, day=1, hour=0, minute=0, second=0, microsecond=0)

    @staticmethod
    def yearly(t):
        """Compute the next year occurrence.

        Args:
            t (datetime.datetime): The reference datetime

        Returns:
            datetime.datetime: First day of next year with hour, minutes, seconds, microseconds set to zero
        """
        y = t.year + 1
        return t.replace(year=y, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)


def parse_size(size):
    """Parse a size string with optional units into bits.

    Supports formats like '100MB', '2GiB', '1.5TB'. Case insensitive.

    Args:
        size (str): Size string to parse (e.g. '100MB', '2GiB')

    Returns:
        float: Size in bits or None if invalid format

    Raises:
        ValueError: If numeric value or unit is invalid
    """
    size = size.strip()
    reg = re.compile(r"([e\+\-\.\d]+)\s*([kmgtpezy])?(i)?(b)", flags=re.I)

    match = reg.fullmatch(size)

    if not match:
        return None

    s, u, i, b = match.groups()

    try:
        s = float(s)
    except ValueError as e:
        raise ValueError("Invalid float value while parsing size: '%s'" % s) from e

    u = "kmgtpezy".index(u.lower()) + 1 if u else 0
    i = 1024 if i else 1000
    b = {"b": 8, "B": 1}[b] if b else 1
    return s * i**u / b


def parse_duration(duration):
    """
    Parses a duration string and returns a corresponding `datetime.timedelta` object.

    The duration string can contain multiple time units, such as years, months, weeks, days, hours, minutes, seconds,
    milliseconds, and microseconds. Units can be specified in singular or plural forms, and multiple units can be
    separated by spaces or commas.

    Supported units:
        - y, year, years
        - month, months
        - w, week, weeks
        - d, day, days
        - h, hour, hours
        - min, minute, minutes
        - s, sec, second, seconds
        - ms, millisecond, milliseconds
        - us, microsecond, microseconds

    Examples:
        parse_duration("1h 30min")        # 1 hour and 30 minutes
        parse_duration("2 days, 3h")      # 2 days and 3 hours
        parse_duration("1.5y 2months")    # 1.5 years and 2 months

    Args:
        duration (str): The duration string to parse.

    Returns:
        datetime.timedelta: The parsed duration as a timedelta object, or None if the input is invalid.

    Raises:
        ValueError: If a value cannot be converted to float or if an invalid unit is encountered.
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


def parse_frequency(frequency):
    """
    Parses a frequency string and returns the corresponding Frequencies enum value.

    Supported frequency strings (case-insensitive, leading/trailing spaces ignored):
        - "hourly"
        - "daily"
        - "weekly"
        - "monthly"
        - "yearly"

    Args:
        frequency (str): The frequency string to parse.

    Returns:
        Frequencies: The corresponding Frequencies enum value if recognized.
        None: If the frequency string is not recognized.
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


def parse_day(day):
    """
    Parses a string representing a day of the week and returns its corresponding integer value.

    The function accepts either the full name of the day (e.g., "Monday", "tuesday") or a string
    starting with 'w' followed by a digit (e.g., "w0" for Monday, "w6" for Sunday).

    Parameters:
        day (str): The day to parse. Can be a day name or a string like "w0" to "w6".

    Returns:
        int or None: The integer value corresponding to the day (Monday=0, ..., Sunday=6),
        or None if the input is invalid.

    Raises:
        ValueError: If the input starts with 'w' but the digit is not in the range [0-6].
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


def parse_time(time):
    """
    Parse a string representing a time and return a `datetime.time` object.

    The function attempts to match the input string against several common time formats,
    including 24-hour and 12-hour representations, with optional seconds, microseconds,
    and AM/PM indicators. If the string does not match any supported format, a ValueError
    is raised.

    Supported formats include:
        - "HH"
        - "HH:MM"
        - "HH:MM:SS"
        - "HH:MM:SS.ssssss"
        - "HH AM/PM"
        - "HH:MM SS"
        - "HH:MM:SS AM/PM"
        - "HH:MM:SS.ssssss AM/PM"

    Args:
        time (str): The time string to parse.

    Returns:
        datetime.time: The parsed time object if successful.

    Raises:
        ValueError: If the input string does not match any recognized time format.

    Examples:
        >>> parse_time("14:30")
        datetime.time(14, 30)
        >>> parse_time("2:30 PM")
        datetime.time(14, 30)
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


def parse_daytime(daytime):
    """
    Parses a string representing a day and time, separated by 'at'.

    The input string should be in the format "<day> at <time>", but if the separator is not found,
    the entire string is used for both day and time parsing.

    Args:
        daytime (str): The string containing the day and time information.

    Returns:
        tuple: A tuple (parsed_day, parsed_time) where parsed_day and parsed_time are the results
               of parsing the day and time respectively. If both cannot be parsed, returns None.

    Raises:
        ValueError: If the day or time part cannot be parsed.
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
