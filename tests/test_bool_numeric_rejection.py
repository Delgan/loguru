"""bool subclasses int/Real; True must not silently become 1."""
import sys

import pytest

from loguru import logger
from loguru._file_sink import FileSink


@pytest.mark.parametrize("value", [True, False])
def test_retention_rejects_bool(value):
    with pytest.raises(TypeError):
        FileSink._make_retention_function(value)


@pytest.mark.parametrize("value", [True, False])
def test_rotation_rejects_bool(value):
    with pytest.raises(TypeError):
        FileSink._make_rotation_function(value)


def test_retention_and_rotation_still_accept_int():
    assert FileSink._make_retention_function(0) is not None
    assert FileSink._make_retention_function(1) is not None
    assert FileSink._make_rotation_function(1) is not None


@pytest.mark.parametrize("value", [True, False])
def test_level_no_rejects_bool(value):
    with pytest.raises(TypeError, match="level no"):
        logger.level("COOKBOOLLEVEL", no=value)


@pytest.mark.parametrize("value", [True, False])
def test_remove_rejects_bool(value):
    with pytest.raises(TypeError, match="handler id"):
        logger.remove(value)


@pytest.mark.parametrize("value", [True, False])
def test_add_level_rejects_bool(value):
    with pytest.raises(TypeError, match="level"):
        logger.add(sys.stderr, level=value)


@pytest.mark.parametrize("value", [True, False])
def test_log_rejects_bool_level(value):
    logger.remove()
    logger.add(sys.stderr)
    try:
        with pytest.raises(TypeError, match="level"):
            logger.log(value, "msg")
    finally:
        logger.remove()
