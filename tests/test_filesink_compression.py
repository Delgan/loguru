import pytest
import os
import re
from loguru import logger


@pytest.mark.parametrize('compression', [
    'gz', 'bz2', 'zip', 'xz', 'lzma', 'tar',
    'tar.gz', 'tar.bz2', 'tar.xz', 'tar.lzma',
    '.tgz', '.tbz2', '.txz', '.tlz', '.tb2', '.tbz'
])
def test_compression_ext(tmpdir, compression):
    i = logger.start(tmpdir.join('{n}.log'), compression=compression)
    logger.stop(i)

    assert len(tmpdir.listdir()) == 1
    assert tmpdir.join('0.log.%s' % compression.lstrip('.')).check(exists=1)

def test_compression_function(tmpdir):
    def compress(file):
        os.replace(file, file + '.rar')

    i = logger.start(tmpdir.join('{n}.log'), compression=compress)
    logger.stop(i)

    assert len(tmpdir.listdir()) == 1
    assert tmpdir.join('0.log.rar').check(exists=1)

def test_compression_at_rotation(tmpdir):
    i = logger.start(tmpdir.join('{n}.log'), rotation=0, compression='gz')
    logger.debug("test")

    assert len(tmpdir.listdir()) == 2
    assert tmpdir.join('0.log.gz').check(exists=1)

def test_no_compression_at_stop_if_rotation(tmpdir):
    i = logger.start(tmpdir.join('test.log'), rotation="10 MB", compression="gz")
    logger.debug("test")
    logger.stop(i)

    assert len(tmpdir.listdir()) == 1
    assert tmpdir.join("test.log").check(exists=1)

def test_compression_renamed_file(tmpdir):
    i = logger.start(tmpdir.join('test.log'), compression="gz")
    logger.debug("test")
    logger.stop(i)

    assert len(tmpdir.listdir()) == 1
    assert re.match(r'test\.log\.[A-Z0-9]+\.gz', tmpdir.listdir()[0].basename)

@pytest.mark.parametrize('compression', [0, 1, os, object(), {"zip"}, "rar", ".7z", "tar.zip"])
def test_invalid_compression(compression):
    with pytest.raises(ValueError):
        logger.start('test.log', compression=compression)
