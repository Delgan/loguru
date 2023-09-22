import os
import sys
import threading
import time
from unittest.mock import Mock

import pytest

from loguru import logger

from .conftest import check_dir


@pytest.mark.parametrize(
    "compression", ["gz", "bz2", "zip", "xz", "lzma", "tar", "tar.gz", "tar.bz2", "tar.xz"]
)
def test_compression_ext(tmp_path, compression):
    i = logger.add(tmp_path / "file.log", compression=compression)
    logger.remove(i)

    check_dir(tmp_path, files=[("file.log.%s" % compression, None)])


def test_compression_function(tmp_path):
    def compress(file):
        os.replace(file, file + ".rar")

    i = logger.add(tmp_path / "file.log", compression=compress)
    logger.remove(i)

    check_dir(tmp_path, files=[("file.log.rar", None)])


@pytest.mark.parametrize("mode", ["a", "a+", "w", "x"])
def test_compression_at_rotation(tmp_path, mode, freeze_time):
    with freeze_time("2010-10-09 11:30:59"):
        logger.add(
            tmp_path / "file.log", format="{message}", rotation=0, compression="gz", mode=mode
        )
        logger.debug("After compression")

    check_dir(
        tmp_path,
        files=[
            ("file.2010-10-09_11-30-59_000000.log.gz", None),
            ("file.log", "After compression\n"),
        ],
    )


@pytest.mark.parametrize("mode", ["a", "a+", "w", "x"])
def test_compression_at_remove_without_rotation(tmp_path, mode):
    i = logger.add(tmp_path / "file.log", compression="gz", mode=mode)
    logger.debug("test")
    logger.remove(i)

    check_dir(tmp_path, files=[("file.log.gz", None)])


@pytest.mark.parametrize("mode", ["a", "a+", "w", "x"])
def test_no_compression_at_remove_with_rotation(tmp_path, mode):
    i = logger.add(tmp_path / "test.log", compression="gz", rotation="100 MB", mode=mode)
    logger.debug("test")
    logger.remove(i)

    check_dir(tmp_path, files=[("test.log", None)])


def test_rename_existing_with_creation_time(tmp_path, freeze_time):
    with freeze_time("2018-01-01") as frozen:
        i = logger.add(tmp_path / "test.log", compression="tar.gz")
        logger.debug("test")
        logger.remove(i)
        frozen.tick()
        j = logger.add(tmp_path / "test.log", compression="tar.gz")
        logger.debug("test")
        logger.remove(j)

    check_dir(
        tmp_path,
        files=[("test.2018-01-01_00-00-00_000000.log.tar.gz", None), ("test.log.tar.gz", None)],
    )


def test_renaming_compression_dest_exists(freeze_time, tmp_path):
    with freeze_time("2019-01-02 03:04:05.000006"):
        for i in range(4):
            logger.add(tmp_path / "rotate.log", compression=".tar.gz", format="{message}")
            logger.info(str(i))
            logger.remove()

    check_dir(
        tmp_path,
        files=[
            ("rotate.log.tar.gz", None),
            ("rotate.2019-01-02_03-04-05_000006.log.tar.gz", None),
            ("rotate.2019-01-02_03-04-05_000006.2.log.tar.gz", None),
            ("rotate.2019-01-02_03-04-05_000006.3.log.tar.gz", None),
        ],
    )


def test_renaming_compression_dest_exists_with_time(freeze_time, tmp_path):
    with freeze_time("2019-01-02 03:04:05.000006"):
        for i in range(4):
            logger.add(tmp_path / "rotate.{time}.log", compression=".tar.gz", format="{message}")
            logger.info(str(i))
            logger.remove()

    check_dir(
        tmp_path,
        files=[
            ("rotate.2019-01-02_03-04-05_000006.log.tar.gz", None),
            ("rotate.2019-01-02_03-04-05_000006.2019-01-02_03-04-05_000006.log.tar.gz", None),
            ("rotate.2019-01-02_03-04-05_000006.2019-01-02_03-04-05_000006.2.log.tar.gz", None),
            ("rotate.2019-01-02_03-04-05_000006.2019-01-02_03-04-05_000006.3.log.tar.gz", None),
        ],
    )


def test_compression_use_renamed_file_after_rotation(tmp_path, freeze_time):
    def rotation(message, _):
        return message.record["extra"].get("rotate", False)

    compression = Mock()

    with freeze_time("2020-01-02"):
        logger.add(
            tmp_path / "test.log", format="{message}", compression=compression, rotation=rotation
        )

        logger.info("Before")
        logger.bind(rotate=True).info("Rotation")
        logger.info("After")

    compression.assert_called_once_with(str(tmp_path / "test.2020-01-02_00-00-00_000000.log"))

    check_dir(
        tmp_path,
        files=[
            ("test.2020-01-02_00-00-00_000000.log", "Before\n"),
            ("test.log", "Rotation\nAfter\n"),
        ],
    )


def test_threaded_compression_after_rotation(tmp_path):
    thread = None

    def rename(filepath):
        time.sleep(1)
        os.rename(filepath, str(tmp_path / "test.log.mv"))

    def compression(filepath):
        nonlocal thread
        thread = threading.Thread(target=rename, args=(filepath,))
        thread.start()

    def rotation(message, _):
        return message.record["extra"].get("rotate", False)

    logger.add(
        tmp_path / "test.log", format="{message}", compression=compression, rotation=rotation
    )

    logger.info("Before")
    logger.bind(rotate=True).info("Rotation")
    logger.info("After")

    thread.join()

    check_dir(
        tmp_path,
        files=[
            ("test.log", "Rotation\nAfter\n"),
            ("test.log.mv", "Before\n"),
        ],
    )


@pytest.mark.parametrize("delay", [True, False])
def test_exception_during_compression_at_rotation(freeze_time, tmp_path, capsys, delay):
    with freeze_time("2017-07-01") as frozen:
        logger.add(
            tmp_path / "test.log",
            format="{message}",
            compression=Mock(side_effect=[Exception("Compression error"), None]),
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
            ("test.2017-07-01_00-00-00_000000.log", ""),
            ("test.2017-07-01_00-00-01_000000.log", ""),
            ("test.log", "BBB\n"),
        ],
    )

    out, err = capsys.readouterr()
    assert out == ""
    assert err.count("Logging error in Loguru Handler") == 1
    assert err.count("Exception: Compression error") == 1


@pytest.mark.parametrize("delay", [True, False])
def test_exception_during_compression_at_rotation_not_caught(freeze_time, tmp_path, capsys, delay):
    with freeze_time("2017-07-01") as frozen:
        logger.add(
            tmp_path / "test.log",
            format="{message}",
            compression=Mock(side_effect=[OSError("Compression error"), None]),
            rotation=0,
            catch=False,
            delay=delay,
        )
        with pytest.raises(OSError, match="Compression error"):
            logger.debug("AAA")

        frozen.tick()
        logger.debug("BBB")

    check_dir(
        tmp_path,
        files=[
            ("test.2017-07-01_00-00-00_000000.log", ""),
            ("test.2017-07-01_00-00-01_000000.log", ""),
            ("test.log", "BBB\n"),
        ],
    )

    out, err = capsys.readouterr()
    assert out == err == ""


@pytest.mark.parametrize("delay", [True, False])
def test_exception_during_compression_at_remove(tmp_path, capsys, delay):
    i = logger.add(
        tmp_path / "test.log",
        format="{message}",
        compression=Mock(side_effect=[OSError("Compression error"), None]),
        catch=True,
        delay=delay,
    )
    logger.debug("AAA")

    with pytest.raises(OSError, match=r"Compression error"):
        logger.remove(i)

    logger.debug("Nope")

    check_dir(
        tmp_path,
        files=[
            ("test.log", "AAA\n"),
        ],
    )

    out, err = capsys.readouterr()
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
    with monkeypatch.context() as context:
        context.setitem(sys.modules, "gzip", None)
        with pytest.raises(ImportError):
            logger.add("test.log", compression=ext)


@pytest.mark.parametrize("ext", ["bz2", "tar.bz2"])
def test_bz2_module_unavailable(ext, monkeypatch):
    with monkeypatch.context() as context:
        context.setitem(sys.modules, "bz2", None)
        with pytest.raises(ImportError):
            logger.add("test.log", compression=ext)


@pytest.mark.parametrize("ext", ["xz", "lzma", "tar.xz"])
def test_lzma_module_unavailable(ext, monkeypatch):
    with monkeypatch.context() as context:
        context.setitem(sys.modules, "lzma", None)
        with pytest.raises(ImportError):
            logger.add("test.log", compression=ext)


@pytest.mark.parametrize("ext", ["tar", "tar.gz", "tar.bz2", "tar.xz"])
def test_tarfile_module_unavailable(ext, monkeypatch):
    with monkeypatch.context() as context:
        context.setitem(sys.modules, "tarfile", None)
        with pytest.raises(ImportError):
            logger.add("test.log", compression=ext)


@pytest.mark.parametrize("ext", ["zip"])
def test_zipfile_module_unavailable(ext, monkeypatch):
    with monkeypatch.context() as context:
        context.setitem(sys.modules, "zipfile", None)
        with pytest.raises(ImportError):
            logger.add("test.log", compression=ext)
