import datetime
import os
from unittest.mock import Mock

import pytest

from loguru import logger

from .conftest import check_dir


@pytest.mark.parametrize("retention", ["1 hour", "1H", " 1 h ", datetime.timedelta(hours=1)])
def test_retention_time(freeze_time, tmp_path, retention):
    i = logger.add(tmp_path / "test.log.x", retention=retention)
    logger.debug("test")
    logger.remove(i)

    check_dir(tmp_path, size=1)

    future = datetime.datetime.now() + datetime.timedelta(days=1)
    with freeze_time(future):
        i = logger.add(tmp_path / "test.log", retention=retention)
        logger.debug("test")

        check_dir(tmp_path, size=2)
        logger.remove(i)
        check_dir(tmp_path, size=0)


@pytest.mark.parametrize("retention", [0, 1, 10])
def test_retention_count(tmp_path, retention):
    file = tmp_path / "test.log"

    for i in range(retention):
        tmp_path.joinpath("test.2011-01-01_01-01-%d_000001.log" % i).write_text("test")

    i = logger.add(file, retention=retention)
    logger.debug("test")
    logger.remove(i)

    check_dir(tmp_path, size=retention)


def test_retention_function(tmp_path):
    def func(logs):
        for log in logs:
            os.rename(log, log + ".xyz")

    tmp_path.joinpath("test.log.1").write_text("A")
    tmp_path.joinpath("test").write_text("B")

    i = logger.add(tmp_path / "test.log", retention=func)
    logger.remove(i)

    check_dir(
        tmp_path,
        files=[
            ("test.log.1.xyz", "A"),
            ("test", "B"),
            ("test.log.xyz", ""),
        ],
    )


def test_managed_files(tmp_path):
    others = {
        "test.log",
        "test.log.1",
        "test.log.1.gz",
        "test.log.rar",
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
        tmp_path.joinpath(other).write_text(other)

    i = logger.add(tmp_path / "test.log", retention=0, catch=False)
    logger.remove(i)

    check_dir(tmp_path, size=0)


def test_not_managed_files(tmp_path):
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
        tmp_path.joinpath(other).write_text(other)

    i = logger.add(tmp_path / "test.log", retention=0, catch=False)
    logger.remove(i)

    assert set(f.name for f in tmp_path.iterdir()) == others


@pytest.mark.parametrize("filename", ["test", "test.log"])
def test_no_duplicates_in_listed_files(tmp_path, filename):
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

    for other in others:
        tmp_path.joinpath(other).write_text(other)

    retention = Mock()
    i = logger.add(tmp_path / filename, retention=retention, catch=False)
    logger.remove(i)

    assert retention.call_count == 1
    assert len(retention.call_args.args[0]) == len(set(retention.call_args.args[0]))


def test_directories_ignored(tmp_path):
    others = ["test.log.2", "test.123.log", "test.log.tar.gz", "test.archive"]

    for other in others:
        tmp_path.joinpath(other).mkdir()

    i = logger.add(tmp_path / "test.log", retention=0, catch=False)
    logger.remove(i)

    check_dir(tmp_path, size=len(others))


def test_manage_formatted_files(freeze_time, tmp_path):
    with freeze_time("2018-01-01 00:00:00"):
        f1 = tmp_path / "temp/2018/file.log"
        f2 = tmp_path / "temp/file2018.log"
        f3 = tmp_path / "temp/d2018/f2018.2018.log"

        a = logger.add(tmp_path / "temp/{time:YYYY}/file.log", retention=0)
        b = logger.add(tmp_path / "temp/file{time:YYYY}.log", retention=0)
        c = logger.add(tmp_path / "temp/d{time:YYYY}/f{time:YYYY}.{time:YYYY}.log", retention=0)

        logger.debug("test")

        assert f1.exists()
        assert f2.exists()
        assert f3.exists()

        logger.remove(a)
        logger.remove(b)
        logger.remove(c)

        assert not f1.exists()
        assert not f2.exists()
        assert not f3.exists()


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support '*' in filename")
def test_date_with_dot_after_extension(tmp_path):
    file = tmp_path / "file.{time:YYYY.MM}_log"

    i = logger.add(tmp_path / "file*.log", retention=0, catch=False)
    logger.remove(i)

    assert not file.exists()


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support '*' in filename")
def test_symbol_in_filename(tmp_path):
    file = tmp_path / "file123.log"
    file.touch()

    i = logger.add(tmp_path / "file*.log", retention=0, catch=False)
    logger.remove(i)

    assert file.exists()


def test_manage_file_without_extension(tmp_path):
    file = tmp_path / "file"

    i = logger.add(file, retention=0)
    logger.debug("?")
    check_dir(tmp_path, files=[("file", None)])
    logger.remove(i)
    check_dir(tmp_path, files=[])


def test_manage_formatted_files_without_extension(tmp_path):
    tmp_path.joinpath("file_8").touch()
    tmp_path.joinpath("file_7").touch()
    tmp_path.joinpath("file_6").touch()

    i = logger.add(tmp_path / "file_{time}", retention=0)
    logger.debug("1")
    logger.remove(i)

    check_dir(tmp_path, size=0)


@pytest.mark.parametrize("mode", ["a", "a+", "w", "x"])
def test_retention_at_rotation(tmp_path, mode):
    tmp_path.joinpath("test.log.1").touch()
    tmp_path.joinpath("test.log.2").touch()
    tmp_path.joinpath("test.log.3").touch()

    logger.add(tmp_path / "test.log", retention=1, rotation=0, mode=mode)
    logger.debug("test")

    check_dir(tmp_path, size=2)


@pytest.mark.parametrize("mode", ["a", "a+", "w", "x"])
def test_retention_at_remove_without_rotation(tmp_path, mode):
    i = logger.add(tmp_path / "file.log", retention=0, mode=mode)
    logger.debug("1")
    check_dir(tmp_path, size=1)
    logger.remove(i)
    check_dir(tmp_path, size=0)


@pytest.mark.parametrize("mode", ["w", "x", "a", "a+"])
def test_no_retention_at_remove_with_rotation(tmp_path, mode):
    i = logger.add(tmp_path / "file.log", retention=0, rotation="100 MB", mode=mode)
    logger.debug("1")
    check_dir(tmp_path, size=1)
    logger.remove(i)
    check_dir(tmp_path, size=1)


def test_no_renaming(tmp_path):
    i = logger.add(tmp_path / "test.log", format="{message}", retention=10)
    logger.debug("test")
    logger.remove(i)

    check_dir(tmp_path, files=[("test.log", "test\n")])


@pytest.mark.parametrize("delay", [True, False])
def test_exception_during_retention_at_rotation(freeze_time, tmp_path, capsys, delay):
    with freeze_time("2022-02-22") as frozen:
        logger.add(
            tmp_path / "test.log",
            format="{message}",
            retention=Mock(side_effect=[Exception("Retention error"), None]),
            rotation=0,
            catch=True,
            delay=delay,
        )
        logger.debug("AAA")
        frozen.tick()
        logger.debug("BBB")

    check_dir(
        tmp_path,
        files=[
            ("test.2022-02-22_00-00-00_000000.log", ""),
            ("test.2022-02-22_00-00-01_000000.log", ""),
            ("test.log", "BBB\n"),
        ],
    )

    out, err = capsys.readouterr()
    assert out == ""
    assert err.count("Logging error in Loguru Handler") == 1
    assert err.count("Exception: Retention error") == 1


@pytest.mark.parametrize("delay", [True, False])
def test_exception_during_retention_at_rotation_not_caught(freeze_time, tmp_path, capsys, delay):
    with freeze_time("2022-02-22") as frozen:
        logger.add(
            tmp_path / "test.log",
            format="{message}",
            retention=Mock(side_effect=[OSError("Retention error"), None]),
            rotation=0,
            catch=False,
            delay=delay,
        )
        with pytest.raises(OSError, match=r"Retention error"):
            logger.debug("AAA")
        frozen.tick()
        logger.debug("BBB")

    check_dir(
        tmp_path,
        files=[
            ("test.2022-02-22_00-00-00_000000.log", ""),
            ("test.2022-02-22_00-00-01_000000.log", ""),
            ("test.log", "BBB\n"),
        ],
    )

    out, err = capsys.readouterr()
    assert out == err == ""


@pytest.mark.parametrize("delay", [True, False])
def test_exception_during_retention_at_remove(tmp_path, capsys, delay):
    i = logger.add(
        tmp_path / "test.log",
        format="{message}",
        retention=Mock(side_effect=[OSError("Retention error"), None]),
        catch=False,
        delay=delay,
    )
    logger.debug("AAA")

    with pytest.raises(OSError, match=r"Retention error"):
        logger.remove(i)

    logger.debug("Nope")

    check_dir(tmp_path, files=[("test.log", "AAA\n")])

    out, err = capsys.readouterr()
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
