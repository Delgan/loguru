import datetime
import os
import sys
import threading
import time

import pytest

import loguru
from loguru import logger


@pytest.mark.parametrize(
    "compression", ["gz", "bz2", "zip", "xz", "lzma", "tar", "tar.gz", "tar.bz2", "tar.xz"]
)
def test_compression_ext(tmpdir, compression):
    i = logger.add(str(tmpdir.join("file.log")), compression=compression)
    logger.remove(i)

    assert len(tmpdir.listdir()) == 1
    assert tmpdir.join("file.log.%s" % compression).check(exists=1)


def test_compression_function(tmpdir):
    def compress(file):
        os.replace(file, file + ".rar")

    i = logger.add(str(tmpdir.join("file.log")), compression=compress)
    logger.remove(i)

    assert len(tmpdir.listdir()) == 1
    assert tmpdir.join("file.log.rar").check(exists=1)


@pytest.mark.parametrize("mode", ["a", "a+", "w", "x"])
def test_compression_at_rotation(tmpdir, mode):
    logger.add(
        str(tmpdir.join("file.log")), format="{message}", rotation=0, compression="gz", mode=mode
    )
    logger.debug("After compression")

    files = sorted(tmpdir.listdir())

    assert len(files) == 2
    assert files[0].fnmatch(
        "file.{0}-{1}-{1}_{1}-{1}-{1}_{2}.log.gz".format("[0-9]" * 4, "[0-9]" * 2, "[0-9]" * 6)
    )
    assert files[1].basename == "file.log"
    assert files[1].read() == "After compression\n"


@pytest.mark.parametrize("mode", ["a", "a+", "w", "x"])
def test_compression_at_remove_without_rotation(tmpdir, mode):
    i = logger.add(str(tmpdir.join("file.log")), compression="gz", mode=mode)
    logger.debug("test")
    logger.remove(i)

    assert len(tmpdir.listdir()) == 1
    assert tmpdir.join("file.log.gz").check(exists=1)


@pytest.mark.parametrize("mode", ["a", "a+", "w", "x"])
def test_no_compression_at_remove_with_rotation(tmpdir, mode):
    i = logger.add(str(tmpdir.join("test.log")), compression="gz", rotation="100 MB", mode=mode)
    logger.debug("test")
    logger.remove(i)

    assert len(tmpdir.listdir()) == 1
    assert tmpdir.join("test.log").check(exists=1)


def test_rename_existing_with_creation_time(monkeypatch, tmpdir):
    def creation_time(filepath):
        assert os.path.isfile(filepath)
        assert os.path.basename(filepath) == "test.log.tar.gz"
        return datetime.datetime(2018, 1, 1, 0, 0, 0, 0).timestamp()

    i = logger.add(str(tmpdir.join("test.log")), compression="tar.gz")
    logger.debug("test")
    logger.remove(i)
    j = logger.add(str(tmpdir.join("test.log")), compression="tar.gz")
    logger.debug("test")

    monkeypatch.setattr(loguru._file_sink, "get_ctime", creation_time)

    logger.remove(j)

    assert len(tmpdir.listdir()) == 2
    assert tmpdir.join("test.log.tar.gz").check(exists=1)
    assert tmpdir.join("test.2018-01-01_00-00-00_000000.log.tar.gz").check(exists=1)


def test_renaming_compression_dest_exists(monkeypatch, monkeypatch_date, tmpdir):
    date = (2019, 1, 2, 3, 4, 5, 6)
    timestamp = datetime.datetime(*date).timestamp()
    monkeypatch_date(*date)
    monkeypatch.setattr(loguru._file_sink, "get_ctime", lambda _: timestamp)

    for i in range(4):
        logger.add(str(tmpdir.join("rotate.log")), compression=".tar.gz", format="{message}")
        logger.info(str(i))
        logger.remove()

    assert len(tmpdir.listdir()) == 4
    assert tmpdir.join("rotate.log.tar.gz").check(exists=1)
    assert tmpdir.join("rotate.2019-01-02_03-04-05_000006.log.tar.gz").check(exists=1)
    assert tmpdir.join("rotate.2019-01-02_03-04-05_000006.2.log.tar.gz").check(exists=1)
    assert tmpdir.join("rotate.2019-01-02_03-04-05_000006.3.log.tar.gz").check(exists=1)


def test_renaming_compression_dest_exists_with_time(monkeypatch, monkeypatch_date, tmpdir):
    date = (2019, 1, 2, 3, 4, 5, 6)
    timestamp = datetime.datetime(*date).timestamp()
    monkeypatch_date(*date)
    monkeypatch.setattr(loguru._file_sink, "get_ctime", lambda _: timestamp)

    for i in range(4):
        logger.add(str(tmpdir.join("rotate.{time}.log")), compression=".tar.gz", format="{message}")
        logger.info(str(i))
        logger.remove()

    assert len(tmpdir.listdir()) == 4
    assert tmpdir.join("rotate.2019-01-02_03-04-05_000006.log.tar.gz").check(exists=1)
    assert tmpdir.join(
        "rotate.2019-01-02_03-04-05_000006.2019-01-02_03-04-05_000006.log.tar.gz"
    ).check(exists=1)
    assert tmpdir.join(
        "rotate.2019-01-02_03-04-05_000006.2019-01-02_03-04-05_000006.2.log.tar.gz"
    ).check(exists=1)
    assert tmpdir.join(
        "rotate.2019-01-02_03-04-05_000006.2019-01-02_03-04-05_000006.3.log.tar.gz"
    ).check(exists=1)


def test_compression_use_renamed_file_after_rotation(tmpdir):
    compressed_file = None

    def compression(filepath):
        nonlocal compressed_file
        compressed_file = filepath

    def rotation(message, _):
        return message.record["extra"].get("rotate", False)

    filepath = tmpdir.join("test.log")
    logger.add(str(filepath), format="{message}", compression=compression, rotation=rotation)

    logger.info("Before")
    logger.bind(rotate=True).info("Rotation")
    logger.info("After")

    assert compressed_file != str(filepath)
    assert open(compressed_file, "r").read() == "Before\n"
    assert filepath.read() == "Rotation\nAfter\n"


def test_threaded_compression_after_rotation(tmpdir):
    thread = None

    def rename(filepath):
        time.sleep(1)
        os.rename(filepath, str(tmpdir.join("test.log.mv")))

    def compression(filepath):
        nonlocal thread
        thread = threading.Thread(target=rename, args=(filepath,))
        thread.start()

    def rotation(message, _):
        return message.record["extra"].get("rotate", False)

    logger.add(
        str(tmpdir.join("test.log")), format="{message}", compression=compression, rotation=rotation
    )

    logger.info("Before")
    logger.bind(rotate=True).info("Rotation")
    logger.info("After")

    thread.join()

    assert tmpdir.join("test.log").read() == "Rotation\nAfter\n"
    assert tmpdir.join("test.log.mv").read() == "Before\n"


@pytest.mark.parametrize("delay", [True, False])
def test_exception_during_compression_at_rotation(tmpdir, capsys, delay):
    raising = True

    def failing_compression(file):
        nonlocal raising
        if raising:
            raising = False
            raise Exception("Compression error")

    logger.add(
        str(tmpdir.join("test.log")),
        format="{message}",
        compression=failing_compression,
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
    assert err.count("Exception: Compression error") == 1


@pytest.mark.parametrize("delay", [True, False])
def test_exception_during_compression_at_rotation_not_caught(tmpdir, capsys, delay):
    raising = True

    def failing_compression(file):
        nonlocal raising
        if raising:
            raising = False
            raise Exception("Compression error")

    logger.add(
        str(tmpdir.join("test.log")),
        format="{message}",
        compression=failing_compression,
        rotation=0,
        catch=False,
        delay=delay,
    )
    with pytest.raises(Exception, match="Compression error"):
        logger.debug("AAA")
    logger.debug("BBB")

    files = sorted(tmpdir.listdir())
    out, err = capsys.readouterr()

    assert len(files) == 3
    assert [file.read() for file in files] == ["", "", "BBB\n"]
    assert out == err == ""


@pytest.mark.parametrize("delay", [True, False])
def test_exception_during_compression_at_remove(tmpdir, capsys, delay):
    raising = True

    def failing_compression(file):
        nonlocal raising
        if raising:
            raising = False
            raise Exception("Compression error")

    i = logger.add(
        str(tmpdir.join("test.log")),
        format="{message}",
        compression=failing_compression,
        catch=True,
        delay=delay,
    )
    logger.debug("AAA")

    with pytest.raises(Exception, match=r"Compression error"):
        logger.remove(i)

    logger.debug("Nope")

    files = sorted(tmpdir.listdir())
    out, err = capsys.readouterr()

    assert len(files) == 1
    assert tmpdir.join("test.log").read() == "AAA\n"
    assert out == err == ""


@pytest.mark.parametrize("compression", [0, True, os, object(), {"zip"}])
def test_invalid_compression(compression):
    with pytest.raises(TypeError):
        logger.add("test.log", compression=compression)


@pytest.mark.parametrize("compression", ["rar", ".7z", "tar.zip", "__dict__"])
def test_unknown_compression(compression):
    with pytest.raises(ValueError):
        logger.add("test.log", compression=compression)


@pytest.mark.parametrize("ext", ["gz", "tar.gz"])
def test_gzip_module_unavailable(ext, monkeypatch):
    monkeypatch.setitem(sys.modules, "gzip", None)
    with pytest.raises(ImportError):
        logger.add("test.log", compression=ext)


@pytest.mark.parametrize("ext", ["bz2", "tar.bz2"])
def test_bz2_module_unavailable(ext, monkeypatch):
    monkeypatch.setitem(sys.modules, "bz2", None)
    with pytest.raises(ImportError):
        logger.add("test.log", compression=ext)


@pytest.mark.parametrize("ext", ["xz", "lzma", "tar.xz"])
def test_lzma_module_unavailable(ext, monkeypatch):
    monkeypatch.setitem(sys.modules, "lzma", None)
    with pytest.raises(ImportError):
        logger.add("test.log", compression=ext)


@pytest.mark.parametrize("ext", ["tar", "tar.gz", "tar.bz2", "tar.xz"])
def test_tarfile_module_unavailable(ext, monkeypatch):
    monkeypatch.setitem(sys.modules, "tarfile", None)
    with pytest.raises(ImportError):
        logger.add("test.log", compression=ext)


@pytest.mark.parametrize("ext", ["zip"])
def test_zipfile_module_unavailable(ext, monkeypatch):
    monkeypatch.setitem(sys.modules, "zipfile", None)
    with pytest.raises(ImportError):
        logger.add("test.log", compression=ext)
