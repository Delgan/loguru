# coding: utf-8

import pytest
import os
from loguru import logger


@pytest.mark.parametrize('compression', ['gz', 'bz2', 'zip', 'xz', 'lzma'])
def test_compression(tmpdir, compression):
    logger.start(tmpdir.join('test.log'), rotation=0, compression=compression, format='{message}')
    logger.debug('a')

    assert tmpdir.join('test.log.1.%s' % compression).check(exists=1)
    assert tmpdir.join('test.log').read() == 'a\n'

def test_compression_function(tmpdir):
    def compress(file):
        os.replace(file, file + '.custom_compression')
    logger.start(tmpdir.join('test.log'), rotation='10 B', compression=compress, format='{message}')
    logger.debug('abc')
    logger.debug('d' * 10)

    assert len(tmpdir.listdir()) == 2
    assert tmpdir.join('test.log').read() == 'd' * 10 + '\n'
    assert tmpdir.join('test.log.1.custom_compression').read() == 'abc\n'

def test_compression_rotation(tmpdir):
    import gzip
    n = logger.start(tmpdir.join('test.log'), rotation=0, compression=True, format='{message}', backups=5)

    for i in range(10):
        logger.debug(str(i))
    logger.stop(n)

    assert tmpdir.join('test.log').read() == '9\n'

    for i in range(5):
        archive = tmpdir.join('test.log.%d.gz' % (i + 1))
        with gzip.open(archive.realpath()) as gz:
            assert gz.read().decode('utf8').replace('\r', '') == '%d\n' % (9 - i - 1)

def test_compression_without_rotation(tmpdir):
    import gzip
    n = logger.start(tmpdir.join('test.log'), compression=True, format='{message}')
    logger.debug("Test")
    logger.stop(n)

    assert len(tmpdir.listdir()) == 1
    archive = tmpdir.join('test.log.gz')
    with gzip.open(archive.realpath()) as gz:
        assert gz.read().decode('utf8').replace('\r', '') == 'Test\n'

def test_compression_backup_file_exists(tmpdir):
    import gzip
    tmpdir.join('test_1.log').write('not compressed')
    logger.start(tmpdir.join('test_{n}.log'), compression=True, format='{message}', rotation='10 B')
    logger.debug('a')
    logger.debug('b' * 10)

    assert len(tmpdir.listdir()) == 3
    assert tmpdir.join('test_1.log').read() == 'b' * 10 + '\n'
    assert tmpdir.join('test_1.log.1').read() == 'not compressed'
    with gzip.open(tmpdir.join('test_0.log.gz').realpath()) as gz:
        assert gz.read().decode('utf8').replace('\r', '') == 'a\n'

def test_compression_0_backups(tmpdir):
    logger.start(tmpdir.join('test.log'), compression=True, rotation=0, backups=0, format='{message}')

    for m in ['a', 'b']:
        logger.debug(m)
        assert len(tmpdir.listdir()) == 1
        assert tmpdir.join('test.log').read() == m + '\n'

@pytest.mark.parametrize('rotate', [True, False])
def test_compression_atexit(tmpdir, rotate, pyexec):
    import gzip

    file_log = tmpdir.join("test.log")
    file_gz = tmpdir.join("test.log.gz")

    start = str(file_log.realpath())
    rotation = '50' if rotate else 'None'

    code = ('logger.start(r"' + start + '", format="{message}", compression="gz", rotation=' + rotation + ')\n'
            'logger.info("It works.")')

    pyexec(code, True)

    if rotate:
        assert file_gz.check(exists=0)
        assert file_log.read() == "It works.\n"
    else:
        assert file_log.check(exists=0)
        with gzip.open(file_gz.realpath()) as gz:
            assert gz.read().decode('utf8').replace('\r', '') == 'It works.\n'

@pytest.mark.parametrize('compression', ['.tar.gz', 0, 1, os, object(), {"zip"}, "rar", ".7z"])
def test_invalid_compression(compression):
    with pytest.raises(ValueError):
        logger.start('test.log', compression=compression)
