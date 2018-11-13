import pytest
import os
from loguru import logger

@pytest.mark.parametrize('compression', [
    'gz', 'bz2', 'zip', 'xz', 'lzma',
    'tar', 'tar.gz', 'tar.bz2', 'tar.xz'
])
def test_compression_ext(tmpdir, compression):
    i = logger.start(tmpdir.join('file.log'), compression=compression)
    logger.stop(i)

    assert len(tmpdir.listdir()) == 1
    assert tmpdir.join("file.log.%s" % compression).check(exists=1)

def test_delayed(tmpdir):
    i = logger.start(tmpdir.join('file.log'), compression='gz', delay=True)
    logger.debug('a')
    logger.stop(i)

    assert len(tmpdir.listdir()) == 1
    assert tmpdir.join("file.log.gz").check(exists=1)

def test_delayed_early_stop(tmpdir):
    i = logger.start(tmpdir.join("file.log"), compression="gz", delay=True)
    logger.stop(i)
    assert len(tmpdir.listdir()) == 0

def test_compression_function(tmpdir):
    def compress(file):
        os.replace(file, file + '.rar')

    i = logger.start(tmpdir.join('file.log'), compression=compress)
    logger.stop(i)

    assert len(tmpdir.listdir()) == 1
    assert tmpdir.join('file.log.rar').check(exists=1)

@pytest.mark.parametrize('mode', ['a', 'a+', 'w', 'x'])
def test_compression_at_rotation(tmpdir, mode):
    i = logger.start(tmpdir.join('file.log'), rotation=0, compression='gz', mode=mode)
    logger.debug("test")

    assert len(tmpdir.listdir()) == 2
    assert tmpdir.join('file.log').check(exists=1)
    assert tmpdir.join('file.log.gz').check(exists=1)

@pytest.mark.parametrize('mode', ['a', 'a+', 'w', 'x'])
def test_compression_at_stop_without_rotation(tmpdir, mode):
    i = logger.start(tmpdir.join('file.log'), compression="gz", mode=mode)
    logger.debug("test")
    logger.stop(i)

    assert len(tmpdir.listdir()) == 1
    assert tmpdir.join('file.log.gz').check(exists=1)

@pytest.mark.parametrize('mode', ['a', 'a+', 'w', 'x'])
def test_no_compression_at_stop_with_rotation(tmpdir, mode):
    i = logger.start(tmpdir.join('test.log'), compression="gz", rotation="100 MB", mode=mode)
    logger.debug("test")
    logger.stop(i)

    assert len(tmpdir.listdir()) == 1
    assert tmpdir.join("test.log").check(exists=1)

def test_rename_existing_before_compression(monkeypatch_date, tmpdir):
    monkeypatch_date(2018, 1, 1, 0, 0, 0, 0)
    i = logger.start(tmpdir.join('test.log'), compression="tar.gz")
    logger.debug("test")
    logger.stop(i)
    j = logger.start(tmpdir.join('test.log'), compression="tar.gz")
    logger.debug("test")
    logger.stop(j)
    assert len(tmpdir.listdir()) == 2
    assert tmpdir.join("test.log.tar.gz").check(exists=1)
    assert tmpdir.join("test.2018-01-01_00-00-00_000000.log.tar.gz").check(exists=1)

@pytest.mark.parametrize('compression', [0, True, os, object(), {"zip"}, "rar", ".7z", "tar.zip"])
def test_invalid_compression(compression):
    with pytest.raises(ValueError):
        logger.start('test.log', compression=compression)
