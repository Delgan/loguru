import pytest
import os
import re
from loguru import logger
import pendulum

@pytest.fixture()
def patch_filename(monkeypatch_now):
    def patched(*a, **k):
        return pendulum.parse("2018-01-01 00:00:00.000000")

    monkeypatch_now(patched)
    yield "file.2018-01-01_00-00-00_000000.log"

@pytest.mark.parametrize('compression', [
    'gz', 'bz2', 'zip', 'xz', 'lzma',
    'tar', 'tar.gz', 'tar.bz2', 'tar.xz'
])
def test_compression_ext(patch_filename, tmpdir, compression):
    i = logger.start(tmpdir.join('file.log'), compression=compression)
    logger.stop(i)

    print(tmpdir.listdir())

    assert len(tmpdir.listdir()) == 1
    assert tmpdir.join('%s.%s' % (patch_filename, compression.lstrip('.'))).check(exists=1)

def test_compression_function(patch_filename, tmpdir):
    def compress(file):
        os.replace(file, file + '.rar')

    i = logger.start(tmpdir.join('file.log'), compression=compress)
    logger.stop(i)

    assert len(tmpdir.listdir()) == 1
    assert tmpdir.join('%s.rar' % patch_filename).check(exists=1)

@pytest.mark.parametrize('mode', ['a', 'w'])
def test_compression_at_rotation(patch_filename, tmpdir, mode):
    i = logger.start(tmpdir.join('file.log'), rotation=0, compression='gz', mode=mode)
    logger.debug("test")

    assert len(tmpdir.listdir()) == 2
    assert tmpdir.join('%s.gz' % patch_filename).check(exists=1)

@pytest.mark.parametrize('mode', ['a', 'w'])
def test_compression_at_stop_without_rotation(patch_filename, tmpdir, mode):
    i = logger.start(tmpdir.join('file.log'), compression="gz", mode=mode)
    logger.debug("test")
    logger.stop(i)

    assert len(tmpdir.listdir()) == 1
    assert tmpdir.join('%s.gz' % patch_filename).check(exists=1)

@pytest.mark.parametrize('mode', ['w', 'x'])
def test_compression_at_stop_with_rotation(patch_filename, tmpdir, mode):
    i = logger.start(tmpdir.join('file.log'), compression="gz", rotation="100 MB", mode=mode)
    logger.debug("test")
    logger.stop(i)

    assert len(tmpdir.listdir()) == 1
    assert tmpdir.join('%s.gz' % patch_filename).check(exists=1)

@pytest.mark.parametrize('mode', ['a', 'a+'])
def test_no_compression_at_stop_with_rotation(tmpdir, mode):
    i = logger.start(tmpdir.join('test.log'), compression="gz", rotation="100 MB", mode=mode)
    logger.debug("test")
    logger.stop(i)

    assert len(tmpdir.listdir()) == 1
    assert tmpdir.join("test.log").check(exists=1)

def test_compression_renamed_file(tmpdir):
    i = logger.start(tmpdir.join('test.log'), compression="gz")
    logger.debug("test")
    logger.stop(i)

    assert len(tmpdir.listdir()) == 1
    assert re.match(r'test\.[0-9\-_]+\.log\.gz', tmpdir.listdir()[0].basename)

@pytest.mark.skip
@pytest.mark.parametrize('ext', ['tar.gz', 'tar.xz', 'tar.bz2'])
def test_not_overriding_previous_file(tmpdir, ext):
    tmpdir.join('test.log.1.tar').write('')
    i = logger.start(tmpdir.join('test.log.{n}'), compression=ext)
    logger.debug('test')
    logger.stop(i)

    assert tmpdir.join('test.log.1.tar').check(exists=1)
    assert tmpdir.join('test.log.1.' + ext).check(exists=1)

@pytest.mark.parametrize('compression', [0, True, os, object(), {"zip"}, "rar", ".7z", "tar.zip"])
def test_invalid_compression(compression):
    with pytest.raises(ValueError):
        logger.start('test.log', compression=compression)
