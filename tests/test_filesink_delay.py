import datetime
import time

from loguru import logger

from .conftest import check_dir


def test_file_not_delayed(tmp_path):
    file = tmp_path / "test.log"
    logger.add(file, format="{message}", delay=False)
    assert file.read_text() == ""
    logger.debug("Not delayed")
    assert file.read_text() == "Not delayed\n"


def test_file_delayed(tmp_path):
    file = tmp_path / "test.log"
    logger.add(file, format="{message}", delay=True)
    assert not file.exists()
    logger.debug("Delayed")
    assert file.read_text() == "Delayed\n"


def test_compression(tmp_path):
    i = logger.add(tmp_path / "file.log", compression="gz", delay=True)
    logger.debug("a")
    logger.remove(i)

    check_dir(tmp_path, files=[("file.log.gz", None)])


def test_compression_early_remove(tmp_path):
    i = logger.add(tmp_path / "file.log", compression="gz", delay=True)
    logger.remove(i)
    check_dir(tmp_path, size=0)


def test_retention(tmp_path):
    for i in range(5):
        tmp_path.joinpath("test.2020-01-01_01-01-%d_000001.log" % i).write_text("test")

    i = logger.add(tmp_path / "test.log", retention=0, delay=True)
    logger.debug("a")
    logger.remove(i)

    check_dir(tmp_path, size=0)


def test_retention_early_remove(tmp_path):
    for i in range(5):
        tmp_path.joinpath("test.2020-01-01_01-01-%d_000001.log" % i).write_text("test")

    i = logger.add(tmp_path / "test.log", retention=0, delay=True)
    logger.remove(i)

    check_dir(tmp_path, size=0)


def test_rotation(tmp_path, freeze_time):
    with freeze_time("2001-02-03"):
        i = logger.add(tmp_path / "file.log", rotation=0, delay=True, format="{message}")
        logger.debug("a")
        logger.remove(i)

    check_dir(
        tmp_path,
        files=[
            ("file.2001-02-03_00-00-00_000000.log", ""),
            ("file.log", "a\n"),
        ],
    )


def test_rotation_early_remove(tmp_path):
    i = logger.add(tmp_path / "file.log", rotation=0, delay=True, format="{message}")
    logger.remove(i)

    check_dir(tmp_path, size=0)


def test_rotation_and_retention(freeze_time, tmp_path):
    with freeze_time("1999-12-12") as frozen:
        filepath = tmp_path / "file.log"
        logger.add(filepath, rotation=30, retention=2, delay=True, format="{message}")
        for i in range(1, 10):
            time.sleep(0.05)  # Retention is based on mtime.
            frozen.tick(datetime.timedelta(seconds=0.05))
            logger.info(str(i) * 20)

    check_dir(
        tmp_path,
        files=[
            ("file.1999-12-12_00-00-00_350000.log", "7" * 20 + "\n"),
            ("file.1999-12-12_00-00-00_400000.log", "8" * 20 + "\n"),
            ("file.log", "9" * 20 + "\n"),
        ],
    )


def test_rotation_and_retention_timed_file(freeze_time, tmp_path):
    with freeze_time("1999-12-12") as frozen:
        filepath = tmp_path / "file.{time}.log"
        logger.add(filepath, rotation=30, retention=2, delay=True, format="{message}")
        for i in range(1, 10):
            time.sleep(0.05)  # Retention is based on mtime.
            frozen.tick(datetime.timedelta(seconds=0.05))
            logger.info(str(i) * 20)

    check_dir(
        tmp_path,
        files=[
            ("file.1999-12-12_00-00-00_350000.log", "7" * 20 + "\n"),
            ("file.1999-12-12_00-00-00_400000.log", "8" * 20 + "\n"),
            ("file.1999-12-12_00-00-00_450000.log", "9" * 20 + "\n"),
        ],
    )
