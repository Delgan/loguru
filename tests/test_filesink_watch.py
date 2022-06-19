import os
from unittest.mock import Mock

import pytest

from loguru import logger

from .conftest import check_dir


@pytest.mark.skipif(os.name == "nt", reason="Windows can't delete file in use")
def test_file_deleted_before_write_without_delay(tmp_path):
    file = tmp_path / "test.log"
    logger.add(file, format="{message}", watch=True, delay=False)
    os.remove(str(file))
    logger.info("Test")
    assert file.read_text() == "Test\n"


@pytest.mark.skipif(os.name == "nt", reason="Windows can't delete file in use")
def test_file_deleted_before_write_with_delay(tmp_path):
    file = tmp_path / "test.log"
    logger.add(file, format="{message}", watch=True, delay=True)
    logger.info("Test 1")
    os.remove(str(file))
    logger.info("Test 2")
    assert file.read_text() == "Test 2\n"


@pytest.mark.skipif(os.name == "nt", reason="Windows can't delete file in use")
def test_file_path_containing_placeholder(tmp_path):
    logger.add(tmp_path / "test_{time}.log", format="{message}", watch=True)
    check_dir(tmp_path, size=1)
    filepath = next(tmp_path.iterdir())
    os.remove(str(filepath))
    logger.info("Test")
    check_dir(tmp_path, size=1)
    assert filepath.read_text() == "Test\n"


@pytest.mark.skipif(os.name == "nt", reason="Windows can't delete file in use")
def test_file_reopened_with_arguments(tmp_path):
    file = tmp_path / "test.log"
    logger.add(file, format="{message}", watch=True, encoding="ascii", errors="replace")
    os.remove(str(file))
    logger.info("é")
    assert file.read_text() == "?\n"


@pytest.mark.skipif(os.name == "nt", reason="Windows can't delete file in use")
def test_file_manually_changed(tmp_path):
    file = tmp_path / "test.log"
    logger.add(file, format="{message}", watch=True, mode="w")
    os.remove(str(file))
    file.write_text("Placeholder")
    logger.info("Test")
    assert file.read_text() == "Test\n"


@pytest.mark.skipif(os.name == "nt", reason="Windows can't delete file in use")
def test_file_folder_deleted(tmp_path):
    file = tmp_path / "foo/bar/test.log"
    logger.add(file, format="{message}", watch=True)
    os.remove(str(file))
    os.rmdir(str(tmp_path / "foo/bar"))
    logger.info("Test")
    assert file.read_text() == "Test\n"


@pytest.mark.skipif(os.name == "nt", reason="Windows can't delete file in use")
def test_file_deleted_before_rotation(tmp_path):
    exists = None
    file = tmp_path / "test.log"

    def rotate(_, __):
        nonlocal exists
        exists = file.exists()
        return False

    logger.add(file, format="{message}", watch=True, rotation=rotate)
    os.remove(str(file))
    logger.info("Test")
    assert exists is True


@pytest.mark.skipif(os.name == "nt", reason="Windows can't delete file in use")
def test_file_deleted_before_compression(tmp_path):
    exists = None
    file = tmp_path / "test.log"

    def compress(_):
        nonlocal exists
        exists = file.exists()
        return False

    logger.add(file, format="{message}", watch=True, compression=compress)
    os.remove(str(file))
    logger.remove()
    assert exists is True


@pytest.mark.skipif(os.name == "nt", reason="Windows can't delete file in use")
def test_file_deleted_before_retention(tmp_path):
    exists = None
    file = tmp_path / "test.log"

    def retain(_):
        nonlocal exists
        exists = file.exists()
        return False

    logger.add(file, format="{message}", watch=True, retention=retain)
    os.remove(str(file))
    logger.remove()
    assert exists is True


def test_file_correctly_reused_after_rotation(tmp_path):
    filepath = tmp_path / "test.log"
    logger.add(
        filepath,
        format="{message}",
        mode="w",
        watch=True,
        rotation=Mock(side_effect=[False, True, False]),
    )
    logger.info("Test 1")
    logger.info("Test 2")
    logger.info("Test 3")
    check_dir(tmp_path, size=2)
    rotated = next(f for f in tmp_path.iterdir() if f != filepath)
    assert rotated.read_text() == "Test 1\n"
    assert filepath.read_text() == "Test 2\nTest 3\n"


@pytest.mark.parametrize("delay", [True, False])
@pytest.mark.parametrize("compression", [None, lambda _: None])
def test_file_closed_without_being_logged(tmp_path, delay, compression):
    filepath = tmp_path / "test.log"
    logger.add(
        filepath,
        format="{message}",
        watch=True,
        delay=delay,
        compression=compression,
    )
    logger.remove()
    assert filepath.exists() is (False if delay else True)
