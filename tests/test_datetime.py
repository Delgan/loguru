import pytest
import datetime
from loguru import logger
import sys


@pytest.mark.parametrize(
    "time_format, date, expected",
    [
        (
            "%Y-%m-%d %H-%M-%S %f %Z",
            (2018, 6, 9, 1, 2, 3, 45, "UTC", 0),
            "2018-06-09 01-02-03 000045 UTC",
        ),
        (
            "YYYY-MM-DD HH-mm-ss SSSSSS zz",
            (2018, 6, 9, 1, 2, 3, 45, "UTC", 0),
            "2018-06-09 01-02-03 000045 UTC",
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
