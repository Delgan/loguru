import datetime
import os

import pytest

from loguru import logger


@pytest.mark.parametrize("retention", ["1 hour", "1H", " 1 h ", datetime.timedelta(hours=1)])
def test_retention_time(monkeypatch_date, tmpdir, retention):
    i = logger.add(str(tmpdir.join("test.log.x")), retention=retention)
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

    i = logger.add(str(tmpdir.join("test.log")), retention=retention)
    logger.debug("test")

    assert len(tmpdir.listdir()) == 2
    logger.remove(i)
    assert len(tmpdir.listdir()) == 0


@pytest.mark.parametrize("retention", [0, 1, 10])
def test_retention_count(tmpdir, retention):
    file = tmpdir.join("test.log")

    for i in range(retention):
        tmpdir.join("test.2011-01-01_01-01-%d_000001.log" % i).write("test")

    i = logger.add(str(file), retention=retention)
    logger.debug("test")
    logger.remove(i)

    assert len(tmpdir.listdir()) == retention


def test_retention_function(tmpdir):
    def func(logs):
        for log in logs:
            os.rename(log, log + ".xyz")

    tmpdir.join("test.log.1").write("")
    tmpdir.join("test").write("")

    i = logger.add(str(tmpdir.join("test.log")), retention=func)
    logger.remove(i)

    assert len(tmpdir.listdir()) == 3
    assert tmpdir.join("test.log.1.xyz").check(exists=1)
    assert tmpdir.join("test.log.xyz").check(exists=1)
    assert tmpdir.join("test").check(exists=1)


def test_managed_files(tmpdir):
    others = {
        "test.log",
        "test.log.1",
        "test.log.1.gz",
        "test.log.rar",
        "test.log",
        "test.2019-11-12_03-22-07_018985.log",
        "test.2019-11-12_03-22-07_018985.log.tar.gz",
        "test.2019-11-12_03-22-07_018985.2.log",
        "test.2019-11-12_03-22-07_018985.2.log.tar.gz",
        "test.foo.log",
        "test.123.log",
        "test.2019-11-12_03-22-07_018985.abc.log",
        "test.2019-11-12_03-22-07_018985.123.abc.log",
        "test.foo.log.bar",
        "test.log.log",
    }

    for other in others:
        tmpdir.join(other).write(other)

    i = logger.add(str(tmpdir.join("test.log")), retention=0, catch=False)
    logger.remove(i)

    assert len(tmpdir.listdir()) == 0


def test_not_managed_files(tmpdir):
    others = {
        "test_.log",
        "_test.log",
        "tes.log",
        "te.st.log",
        "testlog",
        "test",
        "test.tar.gz",
        "test.logs",
        "test.foo",
        "test.foo.logs",
        "tests.logs.zip",
        "foo.test.log",
        "foo.test.log.zip",
    }

    if os.name != "nt":
        others.add("test.")

    for other in others:
        tmpdir.join(other).write(other)

    i = logger.add(str(tmpdir.join("test.log")), retention=0, catch=False)
    logger.remove(i)

    assert set(f.basename for f in tmpdir.listdir()) == others


@pytest.mark.parametrize("filename", ["test", "test.log"])
def test_no_duplicates_in_listed_files(tmpdir, filename):
    matching_files = None
    others = [
        "test.log",
        "test.log.log",
        "test.log.log.log",
        "test",
        "test..",
        "test.log..",
        "test..log",
        "test...log",
        "test.log..",
        "test.log.a.log.b",
    ]

    def retention(files):
        nonlocal matching_files
        matching_files = files

    for other in others:
        tmpdir.join(other).write(other)

    i = logger.add(str(tmpdir.join(filename)), retention=retention, catch=False)
    logger.remove(i)

    assert matching_files is not None
    assert len(matching_files) == len(set(matching_files))


def test_directories_ignored(tmpdir):
    others = ["test.log.2", "test.123.log", "test.log.tar.gz", "test.archive"]

    for other in others:
        tmpdir.join(other).mkdir()

    i = logger.add(str(tmpdir.join("test.log")), retention=0, catch=False)
    logger.remove(i)

    assert len(tmpdir.listdir()) == len(others)


def test_manage_formatted_files(monkeypatch_date, tmpdir):
    monkeypatch_date(2018, 1, 1, 0, 0, 0, 0)

    f1 = tmpdir.join("temp/2018/file.log")
    f2 = tmpdir.join("temp/file2018.log")
    f3 = tmpdir.join("temp/d2018/f2018.2018.log")

    a = logger.add(str(tmpdir.join("temp/{time:YYYY}/file.log")), retention=0)
    b = logger.add(str(tmpdir.join("temp/file{time:YYYY}.log")), retention=0)
    c = logger.add(str(tmpdir.join("temp/d{time:YYYY}/f{time:YYYY}.{time:YYYY}.log")), retention=0)

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


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support '*' in filename")
def test_date_with_dot_after_extension(monkeypatch_date, tmpdir):
    file = tmpdir.join("file.{time:YYYY.MM}_log")

    i = logger.add(str(tmpdir.join("file*.log")), retention=0, catch=False)
    logger.remove(i)

    assert file.check(exists=0)


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support '*' in filename")
def test_symbol_in_filename(tmpdir):
    file = tmpdir.join("file123.log")
    file.write("")

    i = logger.add(str(tmpdir.join("file*.log")), retention=0, catch=False)
    logger.remove(i)

    assert file.check(exists=1)


def test_manage_file_without_extension(tmpdir):
    file = tmpdir.join("file")

    i = logger.add(str(file), retention=0)
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

    i = logger.add(str(tmpdir.join("file_{time}")), retention=0)
    logger.debug("1")
    logger.remove(i)

    assert len(tmpdir.listdir()) == 0


@pytest.mark.parametrize("mode", ["a", "a+", "w", "x"])
def test_retention_at_rotation(tmpdir, mode):
    tmpdir.join("test.log.1").write("")
    tmpdir.join("test.log.2").write("")
    tmpdir.join("test.log.3").write("")

    logger.add(str(tmpdir.join("test.log")), retention=1, rotation=0, mode=mode)
    logger.debug("test")

    assert len(tmpdir.listdir()) == 2


@pytest.mark.parametrize("mode", ["a", "a+", "w", "x"])
def test_retention_at_remove_without_rotation(tmpdir, mode):
    i = logger.add(str(tmpdir.join("file.log")), retention=0, mode=mode)
    logger.debug("1")
    assert len(tmpdir.listdir()) == 1
    logger.remove(i)
    assert len(tmpdir.listdir()) == 0


@pytest.mark.parametrize("mode", ["w", "x", "a", "a+"])
def test_no_retention_at_remove_with_rotation(tmpdir, mode):
    i = logger.add(str(tmpdir.join("file.log")), retention=0, rotation="100 MB", mode=mode)
    logger.debug("1")
    assert len(tmpdir.listdir()) == 1
    logger.remove(i)
    assert len(tmpdir.listdir()) == 1


def test_no_renaming(tmpdir):
    i = logger.add(str(tmpdir.join("test.log")), format="{message}", retention=10)
    logger.debug("test")
    logger.remove(i)

    assert len(tmpdir.listdir()) == 1
    assert tmpdir.join("test.log").read() == "test\n"


@pytest.mark.parametrize("delay", [True, False])
def test_exception_during_retention_at_rotation(tmpdir, capsys, delay):
    raising = True

    def failing_retention(files):
        nonlocal raising
        if raising:
            raising = False
            raise Exception("Retention error")

    logger.add(
        str(tmpdir.join("test.log")),
        format="{message}",
        retention=failing_retention,
        rotation=0,
        catch=True,
        delay=delay,
    )

    logger.debug("AAA")
    logger.debug("BBB")

    files = sorted(tmpdir.listdir())
    out, err = capsys.readouterr()

    assert len(files) == 3
    assert [file.read() for file in files] == ["", "", "BBB\n"]
    assert out == ""
    assert err.count("Logging error in Loguru Handler") == 1
    assert err.count("Exception: Retention error") == 1


@pytest.mark.parametrize("delay", [True, False])
def test_exception_during_retention_at_rotation_not_caught(tmpdir, capsys, delay):
    raising = True

    def failing_retention(files):
        nonlocal raising
        if raising:
            raising = False
            raise Exception("Retention error")

    logger.add(
        str(tmpdir.join("test.log")),
        format="{message}",
        retention=failing_retention,
        rotation=0,
        catch=False,
        delay=delay,
    )

    with pytest.raises(Exception, match=r"Retention error"):
        logger.debug("AAA")

    logger.debug("BBB")

    files = sorted(tmpdir.listdir())
    out, err = capsys.readouterr()

    assert len(files) == 3
    assert [file.read() for file in files] == ["", "", "BBB\n"]
    assert out == err == ""


@pytest.mark.parametrize("delay", [True, False])
def test_exception_during_retention_at_remove(tmpdir, capsys, delay):
    raising = True

    def failing_retention(files):
        nonlocal raising
        if raising:
            raising = False
            raise Exception("Retention error")

    i = logger.add(
        str(tmpdir.join("test.log")),
        format="{message}",
        retention=failing_retention,
        catch=False,
        delay=delay,
    )
    logger.debug("AAA")

    with pytest.raises(Exception, match=r"Retention error"):
        logger.remove(i)

    logger.debug("Nope")

    files = sorted(tmpdir.listdir())
    out, err = capsys.readouterr()

    assert len(files) == 1
    assert tmpdir.join("test.log").read() == "AAA\n"
    assert out == err == ""


@pytest.mark.parametrize("retention", [datetime.time(12, 12, 12), os, object()])
def test_invalid_retention(retention):
    with pytest.raises(TypeError):
        logger.add("test.log", retention=retention)


@pytest.mark.parametrize(
    "retention",
    ["W5", "monday at 14:00", "sunday", "nope", "5 MB", "3 hours 2 dayz", "d", "H", "__dict__"],
)
def test_unkown_retention(retention):
    with pytest.raises(ValueError):
        logger.add("test.log", retention=retention)
