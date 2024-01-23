import datetime
import re
import sys

import freezegun
import pytest

from loguru import logger

if sys.version_info < (3, 6):
    UTC_NAME = "UTC+00:00"
else:
    UTC_NAME = "UTC"


@pytest.mark.parametrize(
    "time_format, date, timezone, expected",
    [
        (
            "%Y-%m-%d %H-%M-%S %f %Z %z",
            "2018-06-09 01:02:03.000045",
            ("UTC", 0),
            "2018-06-09 01-02-03 000045 UTC +0000",
        ),
        (
            "YYYY-MM-DD HH-mm-ss SSSSSS zz ZZ",
            "2018-06-09 01:02:03.000045",
            ("UTC", 0),
            "2018-06-09 01-02-03 000045 UTC +0000",
        ),
        (
            "%Y-%m-%d %H-%M-%S %f %Z %z",
            "2018-06-09 01:02:03.000045",
            ("EST", -18000),
            "2018-06-09 01-02-03 000045 EST -0500",
        ),
        (
            "YYYY-MM-DD HH-mm-ss SSSSSS zz ZZ",
            "2018-06-09 01:02:03.000045",
            ("EST", -18000),
            "2018-06-09 01-02-03 000045 EST -0500",
        ),
        (
            "%Y-%m-%d %H-%M-%S %f %Z!UTC",
            "2018-06-09 01:02:03.000045",
            ("UTC", 0),
            "2018-06-09 01-02-03 000045 %s" % UTC_NAME,
        ),
        (
            "YYYY-MM-DD HH-mm-ss SSSSSS zz!UTC",
            "2018-06-09 01:02:03.000045",
            ("UTC", 0),
            "2018-06-09 01-02-03 000045 %s" % UTC_NAME,
        ),
        (
            "%Y-%m-%d %H-%M-%S %f %Z %z!UTC",
            "2018-06-09 01:02:03.000045",
            ("EST", -18000),
            "2018-06-09 06-02-03 000045 %s +0000" % UTC_NAME,
        ),
        (
            "YYYY-MM-DD HH-mm-ss SSSSSS zz ZZ!UTC",
            "2018-06-09 01:02:03.000045",
            ("UTC", -18000),
            "2018-06-09 06-02-03 000045 %s +0000" % UTC_NAME,
        ),
        (
            "YY-M-D H-m-s SSS Z",
            "2005-04-07 09:03:08.002320",
            ("A", 3600),
            "05-4-7 9-3-8 002 +01:00",
        ),
        (
            "Q_DDDD_DDD d_E h_hh A SS ZZ",
            "2000-01-01 14:00:00.9",
            ("B", -1800),
            "1_001_1 5_6 2_02 PM 90 -0030",
        ),
        ("hh A", "2018-01-01 00:01:02.000003", ("UTC", 0), "12 AM"),
        ("hh A", "2018-01-01 12:00:00.0", ("UTC", 0), "12 PM"),
        ("hh A", "2018-01-01 23:00:00.0", ("UTC", 0), "11 PM"),
        ("[YYYY] MM [DD]", "2018-02-03 11:09:00.000002", ("UTC", 0), "YYYY 02 DD"),
        ("[YYYY MM DD]", "2018-01-03 11:03:04.000002", ("UTC", 0), "[2018 01 03]"),
        ("[[YY]]", "2018-01-03 11:03:04.000002", ("UTC", 0), "[YY]"),
        ("[]", "2018-01-03 11:03:04.000002", ("UTC", 0), ""),
        ("[[]]", "2018-01-03 11:03:04.000002", ("UTC", 0), "[]"),
        ("SSSSSS[]SSS[]SSSSSS", "2018-01-03 11:03:04.100002", ("UTC", 0), "100002100100002"),
        ("[HHmmss", "2018-01-03 11:03:04.000002", ("UTC", 0), "[110304"),
        ("HHmmss]", "2018-01-03 11:03:04.000002", ("UTC", 0), "110304]"),
        ("HH:mm:ss!UTC", "2018-01-01 11:30:00.0", ("A", 7200), "09:30:00"),
        ("UTC! HH:mm:ss", "2018-01-01 11:30:00.0", ("A", 7200), "UTC! 11:30:00"),
        ("!UTC HH:mm:ss", "2018-01-01 11:30:00.0", ("A", 7200), "!UTC 11:30:00"),
        (
            "hh:mm:ss A - Z ZZ !UTC",
            "2018-01-01 12:30:00.0",
            ("A", 5400),
            "11:00:00 AM - +00:00 +0000 ",
        ),
        (
            "YYYY-MM-DD HH:mm:ss[Z]!UTC",
            "2018-01-03 11:03:04.2",
            ("XYZ", -7200),
            "2018-01-03 13:03:04Z",
        ),
        ("HH:mm:ss[!UTC]", "2018-01-01 11:30:00.0", ("A", 7200), "11:30:00!UTC"),
        ("", "2018-02-03 11:09:00.000002", ("Z", 1800), "2018-02-03T11:09:00.000002+0030"),
        ("!UTC", "2018-02-03 11:09:00.000002", ("Z", 1800), "2018-02-03T10:39:00.000002+0000"),
    ],
)
def test_formatting(writer, freeze_time, time_format, date, timezone, expected):
    with freeze_time(date, timezone):
        logger.add(writer, format="{time:%s}" % time_format)
        logger.debug("X")
        result = writer.read()
        assert result == expected + "\n"


@pytest.mark.parametrize(
    "time_format, offset, expected",
    [
        ("%Y-%m-%d %H-%M-%S %f %Z %z", 7230.099, "2018-06-09 01-02-03 000000 ABC +020030.099000"),
        ("YYYY-MM-DD HH-mm-ss zz Z ZZ", 6543, "2018-06-09 01-02-03 ABC +01:49:03 +014903"),
        ("HH-mm-ss zz Z ZZ", -12345.06702, "01-02-03 ABC -03:26:45.067020 -032645.067020"),
    ],
)
@pytest.mark.skipif(sys.version_info < (3, 7), reason="Offset must be a whole number of minutes")
def test_formatting_timezone_offset_down_to_the_second(
    writer, freeze_time, time_format, offset, expected
):
    date = datetime.datetime(2018, 6, 9, 1, 2, 3)
    with freeze_time(date, ("ABC", offset)):
        logger.add(writer, format="{time:%s}" % time_format)
        logger.debug("Test")
        result = writer.read()
        assert result == expected + "\n"


def test_locale_formatting(writer, freeze_time):
    dt = datetime.datetime(2011, 1, 1, 22, 22, 22, 0)
    with freeze_time(dt):
        logger.add(writer, format="{time:MMMM MMM dddd ddd}")
        logger.debug("Test")
        assert writer.read() == dt.strftime("%B %b %A %a\n")


def test_stdout_formatting(freeze_time, capsys):
    with freeze_time("2015-12-25 19:13:18", ("A", 5400)):
        logger.add(sys.stdout, format="{time:YYYY [MM] DD HHmmss Z} {message}")
        logger.debug("Y")
        out, err = capsys.readouterr()
        assert out == "2015 MM 25 191318 +01:30 Y\n"
        assert err == ""


def test_file_formatting(freeze_time, tmp_path):
    with freeze_time("2015-12-25 19:13:18", ("A", -5400)):
        logger.add(tmp_path / "{time:YYYY [MM] DD HHmmss ZZ}.log")
        logger.debug("Z")
        assert list(tmp_path.iterdir()) == [tmp_path / "2015 MM 25 191318 -0130.log"]


def test_missing_struct_time_fields(writer, freeze_time):
    with freeze_time("2011-01-02 03:04:05.6", include_tm_zone=False):
        logger.add(writer, format="{time:YYYY MM DD HH mm ss SSSSSS ZZ zz}")
        logger.debug("X")

        result = writer.read()
        assert re.fullmatch(r"2011 01 02 03 04 05 600000 [+-]\d{4} .*\n", result)


def test_freezegun_mocking(writer):
    logger.add(writer, format="[{time:YYYY MM DD HH:mm:ss}] {message}")

    with freezegun.freeze_time("2000-01-01 18:00:05"):
        logger.info("Frozen")

    assert writer.read() == "[2000 01 01 18:00:05] Frozen\n"


@pytest.mark.parametrize(
    "time_format", ["ss.SSSSSSS", "SS.SSSSSSSS.SS", "HH:mm:ss.SSSSSSSSS", "SSSSSSSSSS"]
)
def test_invalid_time_format(writer, time_format):
    logger.add(writer, format="{time:%s} {message}" % time_format, catch=False)
    with pytest.raises(ValueError, match="Invalid time format"):
        logger.info("Test")
