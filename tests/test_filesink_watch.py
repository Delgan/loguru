import os

import pytest
from loguru import logger


@pytest.mark.skipif(os.name == "nt", reason="Windows can't delete file in use")
def test_file_deleted_before_write_without_delay(tmpdir):
    file = tmpdir.join("test.log")
    logger.add(str(file), format="{message}", watch=True, delay=False)
    os.remove(str(file))
    logger.info("Test")
    assert file.read() == "Test\n"


@pytest.mark.skipif(os.name == "nt", reason="Windows can't delete file in use")
def test_file_deleted_before_write_with_delay(tmpdir):
    file = tmpdir.join("test.log")
    logger.add(str(file), format="{message}", watch=True, delay=True)
    logger.info("Test 1")
    os.remove(str(file))
    logger.info("Test 2")
    assert file.read() == "Test 2\n"


@pytest.mark.skipif(os.name == "nt", reason="Windows can't delete file in use")
def test_file_path_containing_placeholder(tmpdir):
    logger.add(str(tmpdir.join("test_{time}.log")), format="{message}", watch=True)
    assert len(tmpdir.listdir()) == 1
    filepath = tmpdir.listdir()[0]
    os.remove(str(filepath))
    logger.info("Test")
    assert len(tmpdir.listdir()) == 1
    assert filepath.read() == "Test\n"


@pytest.mark.skipif(os.name == "nt", reason="Windows can't delete file in use")
def test_file_reopened_with_arguments(tmpdir):
    file = tmpdir.join("test.log")
    logger.add(str(file), format="{message}", watch=True, encoding="ascii", errors="replace")
    os.remove(str(file))
    logger.info("é")
    assert file.read() == "?\n"


@pytest.mark.skipif(os.name == "nt", reason="Windows can't delete file in use")
def test_file_manually_changed(tmpdir):
    file = tmpdir.join("test.log")
    logger.add(str(file), format="{message}", watch=True, mode="w")
    os.remove(str(file))
    file.write("Placeholder")
    logger.info("Test")
    assert file.read() == "Test\n"


@pytest.mark.skipif(os.name == "nt", reason="Windows can't delete file in use")
def test_file_folder_deleted(tmpdir):
    file = tmpdir.join("foo/bar/test.log")
    logger.add(str(file), format="{message}", watch=True)
    os.remove(str(file))
    os.rmdir(str(tmpdir.join("foo/bar")))
    logger.info("Test")
    assert file.read() == "Test\n"


@pytest.mark.skipif(os.name == "nt", reason="Windows can't delete file in use")
def test_file_deleted_before_rotation(tmpdir):
    exists = None
    file = tmpdir.join("test.log")

    def rotate(_, __):
        nonlocal exists
        exists = file.exists()
        return False

    logger.add(str(file), format="{message}", watch=True, rotation=rotate)
    os.remove(str(file))
    logger.info("Test")
    assert exists is True


@pytest.mark.skipif(os.name == "nt", reason="Windows can't delete file in use")
def test_file_deleted_before_compression(tmpdir):
    exists = None
    file = tmpdir.join("test.log")

    def compress(_):
        nonlocal exists
        exists = file.exists()
        return False

    logger.add(str(file), format="{message}", watch=True, compression=compress)
    os.remove(str(file))
    logger.remove()
    assert exists is True


@pytest.mark.skipif(os.name == "nt", reason="Windows can't delete file in use")
def test_file_deleted_before_retention(tmpdir):
    exists = None
    file = tmpdir.join("test.log")

    def retain(_):
        nonlocal exists
        exists = file.exists()
        return False

    logger.add(str(file), format="{message}", watch=True, retention=retain)
    os.remove(str(file))
    logger.remove()
    assert exists is True


def test_file_correctly_reused_after_rotation(tmpdir):
    rotate = iter((False, True, False))
    filepath = tmpdir.join("test.log")
    logger.add(
        str(filepath),
        format="{message}",
        mode="w",
        watch=True,
        rotation=lambda _, __: next(rotate),
    )
    logger.info("Test 1")
    logger.info("Test 2")
    logger.info("Test 3")
    assert len(tmpdir.listdir()) == 2
    rotated = next(f for f in tmpdir.listdir() if f != filepath)
    assert rotated.read() == "Test 1\n"
    assert filepath.read() == "Test 2\nTest 3\n"


@pytest.mark.parametrize("delay", [True, False])
@pytest.mark.parametrize("compression", [None, lambda _: None])
def test_file_closed_without_being_logged(tmpdir, delay, compression):
    filepath = tmpdir.join("test.log")
    logger.add(
        str(filepath),
        format="{message}",
        watch=True,
        delay=delay,
        compression=compression,
    )
    logger.remove()
    assert filepath.exists() is (False if delay else True)
