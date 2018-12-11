import pytest
import datetime
import os
from loguru import logger


@pytest.mark.parametrize("retention", ["1 hour", "1H", " 1 h ", datetime.timedelta(hours=1)])
def test_retention_time(monkeypatch_date, tmpdir, retention):
    i = logger.add(tmpdir.join("test.log.x"), retention=retention)
    logger.debug("test")
    logger.remove(i)

    assert len(tmpdir.listdir()) == 1

    future = datetime.datetime.now() + datetime.timedelta(days=1)
    monkeypatch_date(
        future.year,
        future.month,
        future.day,
        future.hour,
        future.minute,
        future.second,
        future.microsecond,
    )

    i = logger.add(tmpdir.join("test.log"), retention=retention)
    logger.debug("test")

    assert len(tmpdir.listdir()) == 2
    logger.remove(i)
    assert len(tmpdir.listdir()) == 0


@pytest.mark.parametrize("retention", [0, 1, 10])
def test_retention_count(tmpdir, retention):
    file = tmpdir.join("test.log")

    for i in range(retention):
        tmpdir.join("test.%d.log" % i).write("test")

    i = logger.add(file.realpath(), retention=retention)
    logger.debug("test")
    logger.remove(i)

    assert len(tmpdir.listdir()) == retention


def test_delayed(tmpdir):
    for i in range(5):
        tmpdir.join("test.%d.log" % i).write("test")

    i = logger.add(tmpdir.join("test.log"), retention=0, delay=True)
    logger.debug("a")
    logger.remove(i)

    assert len(tmpdir.listdir()) == 0


def test_delayed_early_remove(tmpdir):
    for i in range(5):
        tmpdir.join("test.%d.log" % i).write("test")

    i = logger.add(tmpdir.join("test.log"), retention=0, delay=True)
    logger.remove(i)

    assert len(tmpdir.listdir()) == 0


def test_retention_function(tmpdir):
    def func(logs):
        for log in logs:
            os.rename(log, log + ".xyz")

    tmpdir.join("test.log.1").write("")
    tmpdir.join("test").write("")

    i = logger.add(tmpdir.join("test.log"), retention=func)
    logger.remove(i)

    assert len(tmpdir.listdir()) == 3
    assert tmpdir.join("test.log.1.xyz").check(exists=1)
    assert tmpdir.join("test.log.xyz").check(exists=1)
    assert tmpdir.join("test").check(exists=1)


def test_managed_files(tmpdir):
    others = ["test.log", "test.log.1", "test.log.1.gz", "test.log.rar", "test.1.log"]

    for other in others:
        tmpdir.join(other).write(other)

    i = logger.add(tmpdir.join("test.log"), retention=0)
    logger.remove(i)

    assert len(tmpdir.listdir()) == 0


def test_not_managed_files(tmpdir):
    others = ["test_.log", "_test.log", "tes.log", "te.st.log", "testlog", "test"]

    for other in others:
        tmpdir.join(other).write(other)

    i = logger.add(tmpdir.join("test.log"), retention=0)
    logger.remove(i)

    assert len(tmpdir.listdir()) == len(others)


def test_manage_formatted_files(monkeypatch_date, tmpdir):
    monkeypatch_date(2018, 1, 1, 0, 0, 0, 0)

    f1 = tmpdir.join("temp/2018/file.log")
    f2 = tmpdir.join("temp/file2018.log")
    f3 = tmpdir.join("temp/d2018/f2018.2018.log")

    a = logger.add(tmpdir.join("temp/{time:YYYY}/file.log"), retention=0)
    b = logger.add(tmpdir.join("temp/file{time:YYYY}.log"), retention=0)
    c = logger.add(tmpdir.join("temp/d{time:YYYY}/f{time:YYYY}.{time:YYYY}.log"), retention=0)

    logger.debug("test")

    assert f1.check(exists=1)
    assert f2.check(exists=1)
    assert f3.check(exists=1)

    logger.remove(a)
    logger.remove(b)
    logger.remove(c)

    assert f1.check(exists=0)
    assert f2.check(exists=0)
    assert f3.check(exists=0)


def test_manage_file_without_extension(tmpdir):
    file = tmpdir.join("file")

    i = logger.add(file, retention=0)
    logger.debug("?")

    assert len(tmpdir.listdir()) == 1
    assert file.check(exists=1)
    logger.remove(i)
    assert len(tmpdir.listdir()) == 0
    assert file.check(exists=0)


def test_manage_formatted_files_without_extension(tmpdir):
    tmpdir.join("file_8").write("")
    tmpdir.join("file_7").write("")
    tmpdir.join("file_6").write("")

    i = logger.add(tmpdir.join("file_{time}"), retention=0)
    logger.debug("1")
    logger.remove(i)

    assert len(tmpdir.listdir()) == 0


@pytest.mark.parametrize("mode", ["a", "a+", "w", "x"])
def test_retention_at_rotation(tmpdir, mode):
    tmpdir.join("test.log.1").write("")
    tmpdir.join("test.log.2").write("")
    tmpdir.join("test.log.3").write("")

    logger.add(tmpdir.join("test.log"), retention=1, rotation=0, mode=mode)
    logger.debug("test")

    assert len(tmpdir.listdir()) == 2


@pytest.mark.parametrize("mode", ["a", "a+", "w", "x"])
def test_retention_at_remove_without_rotation(tmpdir, mode):
    i = logger.add(tmpdir.join("file.log"), retention=0, mode=mode)
    logger.debug("1")
    assert len(tmpdir.listdir()) == 1
    logger.remove(i)
    assert len(tmpdir.listdir()) == 0


@pytest.mark.parametrize("mode", ["w", "x", "a", "a+"])
def test_no_retention_at_remove_with_rotation(tmpdir, mode):
    i = logger.add(tmpdir.join("file.log"), retention=0, rotation="100 MB", mode=mode)
    logger.debug("1")
    assert len(tmpdir.listdir()) == 1
    logger.remove(i)
    assert len(tmpdir.listdir()) == 1


def test_no_renaming(tmpdir):
    i = logger.add(tmpdir.join("test.log"), format="{message}", retention=10)
    logger.debug("test")
    logger.remove(i)

    assert len(tmpdir.listdir()) == 1
    assert tmpdir.join("test.log").read() == "test\n"


@pytest.mark.parametrize(
    "retention",
    [
        "W5",
        "monday at 14:00",
        "sunday",
        "nope",
        "5 MB",
        "3 hours 2 dayz",
        "d",
        "H",
        datetime.time(12, 12, 12),
        os,
        object(),
    ],
)
def test_invalid_retention(retention):
    with pytest.raises(ValueError):
        logger.add("test.log", retention=retention)
