import pytest
import datetime
import os
from loguru import logger


def test_renaming(monkeypatch_date, tmpdir):
    i = logger.add(tmpdir.join("file.log"), rotation=0, format="{message}")

    monkeypatch_date(2018, 1, 1, 0, 0, 0, 0)
    logger.debug("a")
    assert tmpdir.join("file.log").read() == "a\n"
    assert tmpdir.join("file.2018-01-01_00-00-00_000000.log").read() == ""

    monkeypatch_date(2019, 1, 1, 0, 0, 0, 0)
    logger.debug("b")
    assert tmpdir.join("file.log").read() == "b\n"
    assert tmpdir.join("file.2019-01-01_00-00-00_000000.log").read() == "a\n"
    assert tmpdir.join("file.2018-01-01_00-00-00_000000.log").read() == ""


def test_no_renaming(monkeypatch_date, tmpdir):
    monkeypatch_date(2018, 1, 1, 0, 0, 0, 0)
    i = logger.add(tmpdir.join("file_{time}.log"), rotation=0, format="{message}")

    monkeypatch_date(2019, 1, 1, 0, 0, 0, 0)
    logger.debug("a")
    assert tmpdir.join("file_2018-01-01_00-00-00_000000.log").read() == ""
    assert tmpdir.join("file_2019-01-01_00-00-00_000000.log").read() == "a\n"

    monkeypatch_date(2020, 1, 1, 0, 0, 0, 0)
    logger.debug("b")
    assert tmpdir.join("file_2018-01-01_00-00-00_000000.log").read() == ""
    assert tmpdir.join("file_2019-01-01_00-00-00_000000.log").read() == "a\n"
    assert tmpdir.join("file_2020-01-01_00-00-00_000000.log").read() == "b\n"


def test_delayed(monkeypatch_date, tmpdir):
    monkeypatch_date(2018, 1, 1, 0, 0, 0, 0)
    i = logger.add(tmpdir.join("file.log"), rotation=0, delay=True, format="{message}")
    logger.debug("a")
    logger.remove(i)

    assert len(tmpdir.listdir()) == 2
    assert tmpdir.join("file.log").read() == "a\n"
    assert tmpdir.join("file.2018-01-01_00-00-00_000000.log").read() == ""


def test_delayed_early_remove(monkeypatch_date, tmpdir):
    monkeypatch_date(2018, 1, 1, 0, 0, 0, 0)
    i = logger.add(tmpdir.join("file.log"), rotation=0, delay=True, format="{message}")
    logger.remove(i)

    assert len(tmpdir.listdir()) == 0


@pytest.mark.parametrize("size", [8, 8.0, 7.99, "8 B", "8e-6MB", "0.008 kiB", "64b"])
def test_size_rotation(monkeypatch_date, tmpdir, size):
    monkeypatch_date(2018, 1, 1, 0, 0, 0, 0)

    file = tmpdir.join("test_{time}.log")
    i = logger.add(file.realpath(), format="{message}", rotation=size, mode="w")

    monkeypatch_date(2018, 1, 1, 0, 0, 1, 0)
    logger.debug("abcde")

    monkeypatch_date(2018, 1, 1, 0, 0, 2, 0)
    logger.debug("fghij")

    monkeypatch_date(2018, 1, 1, 0, 0, 3, 0)
    logger.debug("klmno")

    monkeypatch_date(2018, 1, 1, 0, 0, 4, 0)
    logger.remove(i)

    assert len(tmpdir.listdir()) == 3
    assert tmpdir.join("test_2018-01-01_00-00-00_000000.log").read() == "abcde\n"
    assert tmpdir.join("test_2018-01-01_00-00-02_000000.log").read() == "fghij\n"
    assert tmpdir.join("test_2018-01-01_00-00-03_000000.log").read() == "klmno\n"


@pytest.mark.parametrize(
    "when, hours",
    [
        # hours = [Should not trigger, should trigger, should not trigger, should trigger, should trigger]
        ("13", [0, 1, 20, 4, 24]),
        ("13:00", [0.2, 0.9, 23, 1, 48]),
        ("13:00:00", [0.5, 1.5, 10, 15, 72]),
        ("13:00:00.123456", [0.9, 2, 10, 15, 256]),
        ("11:00", [22.9, 0.2, 23, 1, 24]),
        ("w0", [11, 1, 24 * 7 - 1, 1, 24 * 7]),
        ("W0 at 00:00", [10, 24 * 7 - 5, 0.1, 24 * 30, 24 * 14]),
        ("W6", [24, 24 * 28, 24 * 5, 24, 364 * 24]),
        ("saturday", [25, 25 * 12, 0, 25 * 12, 24 * 8]),
        ("w6 at 00", [8, 24 * 7, 24 * 6, 24, 24 * 8]),
        (" W6 at 13 ", [0.5, 1, 24 * 6, 24 * 6, 365 * 24]),
        ("w2  at  11:00:00 AM", [48 + 22, 3, 24 * 6, 24, 366 * 24]),
        ("MoNdAy at 11:00:30.123", [22, 24, 24, 24 * 7, 24 * 7]),
        ("sunday", [0.1, 24 * 7 - 10, 24, 24 * 6, 24 * 7]),
        ("SUNDAY at 11:00", [1, 24 * 7, 2, 24 * 7, 30 * 12]),
        ("sunDAY at 1:0:0.0 pm", [0.9, 0.2, 24 * 7 - 2, 3, 24 * 8]),
        (datetime.time(15), [2, 3, 19, 5, 24]),
        (datetime.time(18, 30, 11, 123), [1, 5.51, 20, 24, 40]),
        ("2 h", [1, 2, 0.9, 0.5, 10]),
        ("1 hour", [0.5, 1, 0.1, 100, 1000]),
        ("7 days", [24 * 7 - 1, 1, 48, 24 * 10, 24 * 365]),
        ("1h 30 minutes", [1.4, 0.2, 1, 2, 10]),
        ("1 w, 2D", [24 * 8, 24 * 2, 24, 24 * 9, 24 * 9]),
        ("1.5d", [30, 10, 0.9, 48, 35]),
        ("1.222 hours, 3.44s", [1.222, 0.1, 1, 1.2, 2]),
        (datetime.timedelta(hours=1), [0.9, 0.2, 0.7, 0.5, 3]),
        (datetime.timedelta(minutes=30), [0.48, 0.04, 0.07, 0.44, 0.5]),
        ("hourly", [0.9, 0.2, 0.8, 3, 1]),
        ("daily", [11, 1, 23, 1, 24]),
        ("WEEKLY", [11, 2, 24 * 6, 24, 24 * 7]),
        ("mOnthLY", [0, 24 * 13, 29 * 24, 60 * 24, 24 * 35]),
        ("monthly", [10 * 24, 30 * 24 * 6, 24, 24 * 7, 24 * 31]),
        ("Yearly ", [100, 24 * 7 * 30, 24 * 300, 24 * 100, 24 * 400]),
    ],
)
def test_time_rotation(monkeypatch_date, tmpdir, when, hours):
    now = datetime.datetime(2017, 6, 18, 12, 0, 0)  # Sunday

    monkeypatch_date(
        now.year, now.month, now.day, now.hour, now.minute, now.second, now.microsecond
    )

    i = logger.add(
        tmpdir.join("test_{time}.log").realpath(), format="{message}", rotation=when, mode="w"
    )

    from loguru._datetime import now as nownow

    for h, m in zip(hours, ["a", "b", "c", "d", "e"]):
        now += datetime.timedelta(hours=h)
        monkeypatch_date(
            now.year, now.month, now.day, now.hour, now.minute, now.second, now.microsecond
        )
        logger.debug(m)

    logger.remove(i)
    assert len(tmpdir.listdir()) == 4
    assert [f.read() for f in sorted(tmpdir.listdir())] == ["a\n", "b\nc\n", "d\n", "e\n"]


def test_time_rotation_dst(monkeypatch_date, tmpdir):
    monkeypatch_date(2018, 10, 27, 5, 0, 0, 0, "CET", 3600)
    i = logger.add(tmpdir.join("test_{time}.log").realpath(), format="{message}", rotation="1 day")
    logger.debug("First")

    monkeypatch_date(2018, 10, 28, 5, 30, 0, 0, "CEST", 7200)
    logger.debug("Second")

    monkeypatch_date(2018, 10, 29, 6, 0, 0, 0, "CET", 3600)
    logger.debug("Third")
    logger.remove(i)

    assert len(tmpdir.listdir()) == 3
    assert tmpdir.join("test_2018-10-27_05-00-00_000000.log").read() == "First\n"
    assert tmpdir.join("test_2018-10-28_05-30-00_000000.log").read() == "Second\n"
    assert tmpdir.join("test_2018-10-29_06-00-00_000000.log").read() == "Third\n"


def test_function_rotation(monkeypatch_date, tmpdir):
    monkeypatch_date(2018, 1, 1, 0, 0, 0, 0)
    x = iter([False, True, False])
    i = logger.add(tmpdir.join("test_{time}.log"), rotation=lambda *_: next(x), format="{message}")
    logger.debug("a")
    assert tmpdir.join("test_2018-01-01_00-00-00_000000.log").read() == "a\n"

    monkeypatch_date(2019, 1, 1, 0, 0, 0, 0)
    logger.debug("b")
    assert tmpdir.join("test_2019-01-01_00-00-00_000000.log").read() == "b\n"

    monkeypatch_date(2020, 1, 1, 0, 0, 0, 0)
    logger.debug("c")

    assert len(tmpdir.listdir()) == 2
    assert tmpdir.join("test_2018-01-01_00-00-00_000000.log").read() == "a\n"
    assert tmpdir.join("test_2019-01-01_00-00-00_000000.log").read() == "b\nc\n"


@pytest.mark.parametrize("mode", ["w", "x"])
def test_rotation_at_remove(monkeypatch_date, tmpdir, mode):
    monkeypatch_date(2018, 1, 1, 0, 0, 0, 0)
    i = logger.add(
        tmpdir.join("test_{time:YYYY}.log"), rotation="10 MB", mode=mode, format="{message}"
    )
    logger.debug("test")
    logger.remove(i)

    assert len(tmpdir.listdir()) == 1
    assert tmpdir.join("test_2018.log").read() == "test\n"


@pytest.mark.parametrize("mode", ["a", "a+"])
def test_no_rotation_at_remove(tmpdir, mode):
    i = logger.add(tmpdir.join("test.log"), rotation="10 MB", mode=mode, format="{message}")
    logger.debug("test")
    logger.remove(i)

    assert len(tmpdir.listdir()) == 1
    assert tmpdir.join("test.log").read() == "test\n"


@pytest.mark.parametrize(
    "rotation",
    [
        "w7",
        "w10",
        "w-1",
        "h",
        "M",
        "w1at13",
        "www",
        "13 at w2",
        "w",
        "K",
        "tufy MB",
        "111.111.111 kb",
        "3 Ki",
        "2017.11.12",
        "11:99",
        "monday at 2017",
        "e days",
        "2 days 8 pouooi",
        "foobar",
        "w5 at [not|a|time]",
        "[not|a|day] at 12:00",
        object(),
        os,
        datetime.date(2017, 11, 11),
        datetime.datetime.now(),
        1j,
    ],
)
def test_invalid_rotation(rotation):
    with pytest.raises(ValueError):
        logger.add("test.log", rotation=rotation)
