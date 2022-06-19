import os
from stat import S_IMODE

import pytest

from loguru import logger


@pytest.fixture(scope="module", autouse=True)
def set_umask():
    default = os.umask(0)
    yield
    os.umask(default)


@pytest.mark.parametrize("permissions", [0o777, 0o766, 0o744, 0o700, 0o611])
def test_log_file_permissions(tmp_path, permissions):
    def file_permission_opener(file, flags):
        return os.open(file, flags, permissions)

    filepath = tmp_path / "file.log"
    logger.add(filepath, opener=file_permission_opener)

    logger.debug("Message")
    stat_result = os.stat(str(filepath))
    expected = 0o666 if os.name == "nt" else permissions
    assert S_IMODE(stat_result.st_mode) == expected


@pytest.mark.parametrize("permissions", [0o777, 0o766, 0o744, 0o700, 0o611])
def test_rotation_permissions(tmp_path, permissions, set_umask):
    def file_permission_opener(file, flags):
        return os.open(file, flags, permissions)

    logger.add(tmp_path / "file.log", rotation=0, opener=file_permission_opener)

    logger.debug("Message")

    files = list(tmp_path.iterdir())
    assert len(files) == 2

    for filepath in files:
        stat_result = os.stat(str(filepath))
        expected = 0o666 if os.name == "nt" else permissions
        assert S_IMODE(stat_result.st_mode) == expected
