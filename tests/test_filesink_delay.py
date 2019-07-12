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
        tmpdir.join("test.%d.log" % i).write("test")

    i = logger.add(str(tmpdir.join("test.log")), retention=0, delay=True)
    logger.debug("a")
    logger.remove(i)

    assert len(tmpdir.listdir()) == 0


def test_retention_early_remove(tmpdir):
    for i in range(5):
        tmpdir.join("test.%d.log" % i).write("test")

    i = logger.add(str(tmpdir.join("test.log")), retention=0, delay=True)
    logger.remove(i)

    assert len(tmpdir.listdir()) == 0


def test_rotation(monkeypatch_date, tmpdir):
    monkeypatch_date(2018, 1, 1, 0, 0, 0, 0)
    i = logger.add(str(tmpdir.join("file.log")), rotation=0, delay=True, format="{message}")
    logger.debug("a")
    logger.remove(i)

    assert len(tmpdir.listdir()) == 2
    assert tmpdir.join("file.log").read() == "a\n"
    assert tmpdir.join("file.2018-01-01_00-00-00_000000.log").read() == ""


def test_rotation_early_remove(monkeypatch_date, tmpdir):
    monkeypatch_date(2018, 1, 1, 0, 0, 0, 0)
    i = logger.add(str(tmpdir.join("file.log")), rotation=0, delay=True, format="{message}")
    logger.remove(i)

    assert len(tmpdir.listdir()) == 0
