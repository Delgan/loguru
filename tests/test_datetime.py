import pytest
from loguru import logger


@pytest.fixture(params=["log", "file"])
def format_tester(request, writer, tmpdir):

    mode = request.param

    def test_log(fmt):
        logger.add(writer, format=fmt)
        logger.debug("X")
        result = writer.read().rstrip("\n")
        return result

    def test_file(fmt):
        logger.add(tmpdir.join(fmt))
        logger.debug("X")
        files = tmpdir.listdir()
        assert len(files) == 1
        return files[0].basename

    def format_tester(fmt):
        tests = dict(log=test_log, file=test_file)
        return tests[mode]("{time:%s}" % fmt)

    return format_tester


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
    ],
)
def test_formatting(format_tester, monkeypatch_date, time_format, date, expected):
    monkeypatch_date(*date)
    assert format_tester(time_format) == expected
