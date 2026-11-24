import datetime

import pytest

from loguru import _string_parsers


@pytest.mark.parametrize(
    ("size", "expected"),
    [
        ("1 b", 0.125),
        ("1 B", 1),
        ("1 KB", 1e3),
        ("1 MB", 1e6),
        ("1 GB", 1e9),
        ("1 TB", 1e12),
        ("1 PB", 1e15),
        ("1 EB", 1e18),
        ("1 ZB", 1e21),
        ("1 YB", 1e24),
        ("1 KiB", 1024),
        ("1 Mib", 131072),
        ("1.5 B", 1.5),
        ("1.5e1 KB", 15000),
        ("1.5 KiB", 1536),
        # Specific edge cases due to E being both an exponent marker and a unit prefix.
        ("1.5e1EB", 1.5e19),
        ("1e-1EB", 1e17),
        ("1EB", 1e18),
        ("1EiB", 1024**6),
    ],
)
def test_parse_size(size, expected):
    assert _string_parsers.parse_size(size) == expected


@pytest.mark.parametrize(
    ("aliases", "expected"),
    [
        ("y year years", datetime.timedelta(days=365)),
        ("month months", datetime.timedelta(days=30, hours=10)),
        ("w week weeks", datetime.timedelta(weeks=1)),
        ("d day days", datetime.timedelta(days=1)),
        ("h hour hours", datetime.timedelta(hours=1)),
        ("min mins minute minutes", datetime.timedelta(minutes=1)),
        ("s sec secs second seconds", datetime.timedelta(seconds=1)),
        ("ms millisecond milliseconds", datetime.timedelta(milliseconds=1)),
        ("us microsecond microseconds", datetime.timedelta(microseconds=1)),
    ],
)
def test_parse_duration_units(aliases, expected):
    for unit in aliases.split():
        assert _string_parsers.parse_duration("1 " + unit) == expected


def test_parse_duration_multiple_units():
    duration = datetime.timedelta(hours=1, minutes=49, seconds=30)
    assert _string_parsers.parse_duration("+1.5 H, 2e1 MIN-30s") == duration


@pytest.mark.parametrize(
    ("frequency", "start", "expected"),
    [
        ("hourly", datetime.datetime(2024, 1, 31, 23, 59, 59, 1), datetime.datetime(2024, 2, 1)),
        ("daily", datetime.datetime(2024, 2, 28, 23, 59, 59, 1), datetime.datetime(2024, 2, 29)),
        ("weekly", datetime.datetime(2024, 6, 2, 23, 59, 59, 1), datetime.datetime(2024, 6, 3)),
        ("weekly", datetime.datetime(2024, 6, 3), datetime.datetime(2024, 6, 10)),
        ("monthly", datetime.datetime(2024, 1, 31, 23, 59, 59, 1), datetime.datetime(2024, 2, 1)),
        ("monthly", datetime.datetime(2024, 12, 15, 12, 34, 56, 1), datetime.datetime(2025, 1, 1)),
        ("yearly", datetime.datetime(2024, 2, 29, 12, 34, 56, 1), datetime.datetime(2025, 1, 1)),
    ],
)
def test_parse_frequency(frequency, start, expected):
    assert _string_parsers.parse_frequency(frequency)(start) == expected


@pytest.mark.parametrize(
    ("day", "expected"),
    [
        ("monday", 0),
        ("tuesday", 1),
        ("wednesday", 2),
        ("thursday", 3),
        ("friday", 4),
        ("saturday", 5),
        ("sunday", 6),
    ],
)
def test_parse_day(day, expected):
    assert _string_parsers.parse_day(day) == expected
    assert _string_parsers.parse_day("W%d" % expected) == expected


@pytest.mark.parametrize(
    ("time", "expected"),
    [
        ("23", datetime.time(23)),
        ("23:04", datetime.time(23, 4)),
        ("23:04:05", datetime.time(23, 4, 5)),
        ("23:04:05.6", datetime.time(23, 4, 5, 600000)),
        ("12 am", datetime.time(0)),
        ("12:04 PM", datetime.time(12, 4)),
        ("11:04:05 pm", datetime.time(23, 4, 5)),
        ("11:04:05.6 PM", datetime.time(23, 4, 5, 600000)),
    ],
)
def test_parse_time(time, expected):
    assert _string_parsers.parse_time(time) == expected


@pytest.mark.parametrize(
    ("daytime", "expected"),
    [
        ("Friday at 23:45", (4, datetime.time(23, 45))),
        ("w0", (0, None)),
        ("00:00", (None, datetime.time(0))),
    ],
)
def test_parse_daytime(daytime, expected):
    assert _string_parsers.parse_daytime(daytime) == expected
