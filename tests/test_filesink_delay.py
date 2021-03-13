import re
import time

from loguru import logger


def test_file_not_delayed(tmpdir):
    file = tmpdir.join("test.log")
    logger.add(str(file), format="{message}", delay=False)
    assert file.check(exists=1)
    assert file.read() == ""
    logger.debug("Not delayed")
    assert file.read() == "Not delayed\n"


def test_file_delayed(tmpdir):
    file = tmpdir.join("test.log")
    logger.add(str(file), format="{message}", delay=True)
    assert file.check(exists=0)
    logger.debug("Delayed")
    assert file.read() == "Delayed\n"


def test_compression(tmpdir):
    i = logger.add(str(tmpdir.join("file.log")), compression="gz", delay=True)
    logger.debug("a")
    logger.remove(i)

    assert len(tmpdir.listdir()) == 1
    assert tmpdir.join("file.log.gz").check(exists=1)


def test_compression_early_remove(tmpdir):
    i = logger.add(str(tmpdir.join("file.log")), compression="gz", delay=True)
    logger.remove(i)
    assert len(tmpdir.listdir()) == 0


def test_retention(tmpdir):
    for i in range(5):
        tmpdir.join("test.2020-01-01_01-01-%d_000001.log" % i).write("test")

    i = logger.add(str(tmpdir.join("test.log")), retention=0, delay=True)
    logger.debug("a")
    logger.remove(i)

    assert len(tmpdir.listdir()) == 0


def test_retention_early_remove(tmpdir):
    for i in range(5):
        tmpdir.join("test.2020-01-01_01-01-%d_000001.log" % i).write("test")

    i = logger.add(str(tmpdir.join("test.log")), retention=0, delay=True)
    logger.remove(i)

    assert len(tmpdir.listdir()) == 0


def test_rotation(tmpdir):
    i = logger.add(str(tmpdir.join("file.log")), rotation=0, delay=True, format="{message}")
    logger.debug("a")
    logger.remove(i)

    files = sorted(tmpdir.listdir())

    assert len(files) == 2
    assert re.match(r"file\.[0-9-_]+\.log", files[0].basename)
    assert files[1].basename == "file.log"
    assert files[0].read() == ""
    assert files[1].read() == "a\n"


def test_rotation_early_remove(tmpdir):
    i = logger.add(str(tmpdir.join("file.log")), rotation=0, delay=True, format="{message}")
    logger.remove(i)

    assert len(tmpdir.listdir()) == 0


def test_rotation_and_retention(tmpdir):
    filepath = str(tmpdir.join("file.log"))
    logger.add(filepath, rotation=30, retention=2, delay=True, format="{message}")
    for i in range(1, 10):
        time.sleep(0.02)
        logger.info(str(i) * 20)

    files = sorted(tmpdir.listdir())

    assert len(files) == 3
    assert all(re.match(r"file\.[0-9-_]+\.log", f.basename) for f in files[:2])
    assert files[2].basename == "file.log"
    assert files[0].read() == "7" * 20 + "\n"
    assert files[1].read() == "8" * 20 + "\n"
    assert files[2].read() == "9" * 20 + "\n"


def test_rotation_and_retention_timed_file(tmpdir):
    filepath = str(tmpdir.join("file.{time}.log"))
    logger.add(filepath, rotation=30, retention=2, delay=True, format="{message}")
    for i in range(1, 10):
        time.sleep(0.02)
        logger.info(str(i) * 20)

    files = sorted(tmpdir.listdir())

    assert len(files) == 3
    assert all(re.match(r"file\.[0-9-_]+\.log", f.basename) for f in files)
    assert files[0].read() == "7" * 20 + "\n"
    assert files[1].read() == "8" * 20 + "\n"
    assert files[2].read() == "9" * 20 + "\n"
