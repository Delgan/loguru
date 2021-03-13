import datetime
import re
import sys
import time

import pytest

import loguru
from loguru import logger

if sys.version_info < (3, 6):
    UTC_NAME = "UTC+00:00"
else:
    UTC_NAME = "UTC"


@pytest.mark.parametrize(
    "time_format, date, expected",
    [
        (
            "%Y-%m-%d %H-%M-%S %f %Z %z",
            (2018, 6, 9, 1, 2, 3, 45, "UTC", 0),
            "2018-06-09 01-02-03 000045 UTC +0000",
        ),
        (
            "YYYY-MM-DD HH-mm-ss SSSSSS zz ZZ",
            (2018, 6, 9, 1, 2, 3, 45, "UTC", 0),
            "2018-06-09 01-02-03 000045 UTC +0000",
        ),
        (
            "%Y-%m-%d %H-%M-%S %f %Z %z",
            (2018, 6, 9, 1, 2, 3, 45, "EST", -18000),
            "2018-06-09 01-02-03 000045 EST -0500",
        ),
        (
            "YYYY-MM-DD HH-mm-ss SSSSSS zz ZZ",
            (2018, 6, 9, 1, 2, 3, 45, "EST", -18000),
            "2018-06-09 01-02-03 000045 EST -0500",
        ),
        (
            "%Y-%m-%d %H-%M-%S %f %Z!UTC",
            (2018, 6, 9, 1, 2, 3, 45, "UTC", 0),
            "2018-06-09 01-02-03 000045 %s" % UTC_NAME,
        ),
        (
            "YYYY-MM-DD HH-mm-ss SSSSSS zz!UTC",
            (2018, 6, 9, 1, 2, 3, 45, "UTC", 0),
            "2018-06-09 01-02-03 000045 %s" % UTC_NAME,
        ),
        (
            "%Y-%m-%d %H-%M-%S %f %Z %z!UTC",
            (2018, 6, 9, 1, 2, 3, 45, "EST", -18000),
            "2018-06-09 06-02-03 000045 %s +0000" % UTC_NAME,
        ),
        (
            "YYYY-MM-DD HH-mm-ss SSSSSS zz ZZ!UTC",
            (2018, 6, 9, 1, 2, 3, 45, "UTC", -18000),
            "2018-06-09 06-02-03 000045 %s +0000" % UTC_NAME,
        ),
        ("YY-M-D H-m-s SSS Z", (2005, 4, 7, 9, 3, 8, 2320, "A", 3600), "05-4-7 9-3-8 002 +01:00"),
        (
            "Q_DDDD_DDD d_E h_hh A SS ZZ",
            (2000, 1, 1, 14, 0, 0, 900000, "B", -1800),
            "1_001_1 5_6 2_02 PM 90 -0030",
        ),
        ("hh A", (2018, 1, 1, 0, 1, 2, 3), "12 AM"),
        ("hh A", (2018, 1, 1, 12, 0, 0, 0), "12 PM"),
        ("hh A", (2018, 1, 1, 23, 0, 0, 0), "11 PM"),
        ("[YYYY] MM [DD]", (2018, 2, 3, 11, 9, 0, 2), "YYYY 02 DD"),
        ("[YYYY MM DD]", (2018, 1, 3, 11, 3, 4, 2), "[2018 01 03]"),
        ("[[YY]]", (2018, 1, 3, 11, 3, 4, 2), "[YY]"),
        ("[]", (2018, 1, 3, 11, 3, 4, 2), "[]"),
        #        ("[HHmmss", (2018, 1, 3, 11, 3, 4, 2), "[110304"),  # Fail PyPy
        ("HHmmss]", (2018, 1, 3, 11, 3, 4, 2), "110304]"),
        ("HH:mm:ss!UTC", (2018, 1, 1, 11, 30, 0, 0, "A", 7200), "09:30:00"),
        ("UTC! HH:mm:ss", (2018, 1, 1, 11, 30, 0, 0, "A", 7200), "UTC! 11:30:00"),
        ("!UTC HH:mm:ss", (2018, 1, 1, 11, 30, 0, 0, "A", 7200), "!UTC 11:30:00"),
        (
            "hh:mm:ss A - Z ZZ !UTC",
            (2018, 1, 1, 12, 30, 0, 0, "A", 5400),
            "11:00:00 AM - +00:00 +0000 ",
        ),
        (
            "YYYY-MM-DD HH:mm:ss[Z]!UTC",
            (2018, 1, 3, 11, 3, 4, 2, "XYZ", -7200),
            "2018-01-03 13:03:04Z",
        ),
        ("HH:mm:ss[!UTC]", (2018, 1, 1, 11, 30, 0, 0, "A", 7200), "11:30:00!UTC"),
        ("", (2018, 2, 3, 11, 9, 0, 2, "Z", 1800), "2018-02-03T11:09:00.000002+0030"),
        ("!UTC", (2018, 2, 3, 11, 9, 0, 2, "Z", 1800), "2018-02-03T10:39:00.000002+0000"),
    ],
)
def test_formatting(writer, monkeypatch_date, time_format, date, expected):
    monkeypatch_date(*date)
    logger.add(writer, format="{time:%s}" % time_format)
    logger.debug("X")
    result = writer.read()
    assert result == expected + "\n"


def test_locale_formatting(writer, monkeypatch_date):
    date = (2011, 1, 1, 22, 22, 22, 0)
    monkeypatch_date(*date)
    logger.add(writer, format="{time:MMMM MMM dddd ddd}")
    logger.debug("Test")
    assert writer.read() == datetime.datetime(*date).strftime("%B %b %A %a\n")


def test_stdout_formatting(monkeypatch_date, capsys):
    monkeypatch_date(2015, 12, 25, 19, 13, 18, 0, "A", 5400)
    logger.add(sys.stdout, format="{time:YYYY [MM] DD HHmmss Z} {message}")
    logger.debug("Y")
    out, err = capsys.readouterr()
    assert out == "2015 MM 25 191318 +01:30 Y\n"
    assert err == ""


def test_file_formatting(monkeypatch_date, tmpdir):
    monkeypatch_date(2015, 12, 25, 19, 13, 18, 0, "A", -5400)
    logger.add(str(tmpdir.join("{time:YYYY [MM] DD HHmmss ZZ}.log")))
    logger.debug("Z")
    files = tmpdir.listdir()
    assert len(files) == 1
    result = files[0].basename
    assert result == "2015 MM 25 191318 -0130.log"


def test_missing_struct_time_fields(writer, monkeypatch, monkeypatch_date):
    class struct_time:
        def __init__(self, struct):
            self._struct = struct

        def __getattr__(self, attr):
            if attr in {"tm_gmtoff", "tm_zone"}:
                raise AttributeError
            return getattr(self._struct, attr)

    def localtime(*args, **kwargs):
        local = time.localtime(*args, **kwargs)
        return struct_time(local)

    monkeypatch.setattr(loguru._datetime, "localtime", localtime)

    logger.add(writer, format="{time:YYYY MM DD HH mm ss SSSSSS ZZ zz}")
    logger.debug("X")

    result = writer.read()
    assert re.fullmatch(r"\d{4} \d{2} \d{2} \d{2} \d{2} \d{2} \d{6} [+-]\d{4} .*\n", result)
