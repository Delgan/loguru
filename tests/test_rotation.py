# coding: utf-8

import pytest
import pendulum
import loguru
import datetime
import math
import os
import re
import py

@pytest.mark.parametrize('name, should_rename', [
    ('test.log', True),
    ('{n}.log', False),
    ('{start_time}.log', True),
    ('test.log.{n+1}', False),
    ('test.log.1', True),
])
def test_renaming(tmpdir, logger, name, should_rename):
    file = tmpdir.join(name)
    logger.start(file.realpath(), rotation=0)

    assert len(tmpdir.listdir()) == 1
    basename = tmpdir.listdir()[0].basename

    logger.debug("a")
    logger.debug("b")
    logger.debug("c")

    files = [f.basename for f in tmpdir.listdir()]

    renamed = [basename + '.' + str(i) in files for i in [1, 2, 3]]

    if should_rename:
        assert all(renamed)
    else:
        assert not any(renamed)

@pytest.mark.parametrize('size', [
    8, 8.0, 7.99, "8 B", "8e-6MB", "0.008 kiB", "64b"
])
def test_size_rotation(tmpdir, logger, size):
    file_1 = tmpdir.join("test.log")
    file_2 = tmpdir.join("test.log.1")
    file_3 = tmpdir.join("test.log.2")
    file_4 = tmpdir.join("test.log.3")
    logger.start(file_1.realpath(), format='{message}', rotation=size)

    m1, m2, m3, m4, m5 = 'a' * 5, 'b' * 2, 'c' * 2, 'd' * 4, 'e' * 8

    logger.debug(m1)
    logger.debug(m2)
    logger.debug(m3)
    logger.debug(m4)
    logger.debug(m5)

    assert file_1.read() == m5 + '\n'
    assert file_2.read() == m4 + '\n'
    assert file_3.read() == m2 + '\n' + m3 + '\n'
    assert file_4.read() == m1 + '\n'

@pytest.mark.parametrize('when, hours', [
    # hours = [Should not trigger, should trigger, should not trigger, should trigger, should trigger]
    ('13', [0, 1, 20, 4, 24]),
    ('13:00', [0.2, 0.9, 23, 1, 48]),
    ('13:00:00', [0.5, 1.5, 10, 15, 72]),
    ('13:00:00.123456', [0.9, 2, 10, 15, 256]),
    ('11:00', [22.9, 0.2, 23, 1, 24]),
    ('w0', [11, 1, 24 * 7 - 1, 1, 24 * 7]),
    ('W0 at 00:00', [10, 24 * 7 - 5, 0.1, 24 * 30, 24 * 14]),
    ('W6', [24, 24 * 28, 24 * 5, 24, 364 * 24]),
    ('saturday', [25, 25 * 12, 0, 25 * 12, 24 * 8]),
    ('w6 at 00', [8, 24 * 7, 24 * 6, 24, 24 * 8]),
    (' W6 at 13 ', [0.5, 1, 24 * 6, 24 * 6, 365 * 24]),
    ('w2  at  11:00:00', [48 + 22, 3, 24 * 6, 24, 366 * 24]),
    ('MoNdAy at 11:00:30.123', [22, 24, 24, 24 * 7, 24 * 7]),
    ('sunday', [0.1, 24 * 7 - 10, 24, 24 * 6, 24 * 7]),
    ('SUNDAY at 11:00', [1, 24 * 7, 2, 24*7, 30*12]),
    ('sunDAY at 13:00:00', [0.9, 0.2, 24 * 7 - 2, 3, 24 * 8]),
    (datetime.time(15), [2, 3, 19, 5, 24]),
    (pendulum.Time(18, 30, 11, 123), [1, 5.51, 20, 24, 40]),
    ("2 h", [1, 2, 0.9, 0.5, 10]),
    ("1 hour", [0.5, 1, 0.1, 100, 1000]),
    ("7 days", [24 * 7 - 1, 1, 48, 24 * 10, 24 * 365]),
    ("1h 30 minutes", [1.4, 0.2, 1, 2, 10]),
    ("1 w, 2D", [24 * 8, 24 * 2, 24, 24 * 9, 24 * 9]),
    ("1.5d", [30, 10, 0.9, 48, 35]),
    ("1.222 hours, 3.44s", [1.222, 0.1, 1, 1.2, 2]),
    (datetime.timedelta(hours=1), [0.9, 0.2, 0.7, 0.5, 3]),
    (pendulum.Interval(minutes=30), [0.48, 0.04, 0.07, 0.44, 0.5]),
    (lambda t: t.add(months=1).start_of('month').at(13, 00, 00), [12 * 24, 26, 31 * 24 - 2, 2, 24 * 60]),
    ('hourly', [0.9, 0.2, 0.8, 3, 1]),
    ('daily', [11, 1, 23, 1, 24]),
    ('WEEKLY', [11, 2, 24 * 6, 24, 24 * 7]),
    (' mOnthLY', [0, 24 * 13, 29 * 24, 60 * 24, 24 * 35]),
    ('yearly ', [100, 24 * 7 * 30, 24 * 300, 24 * 100, 24 * 400]),
])
def test_time_rotation(monkeypatch_now, tmpdir, when, hours, logger):
    now = pendulum.parse("2017-06-18 12:00:00")  # Sunday

    monkeypatch_now(lambda *a, **k: now)

    file_1 = tmpdir.join("test.log")
    file_2 = tmpdir.join("test.log.1")
    file_3 = tmpdir.join("test.log.2")
    file_4 = tmpdir.join("test.log.3")

    logger.start(file_1.realpath(), format='{message}', rotation=when)

    m1, m2, m3, m4, m5 = 'a', 'b', 'c', 'd', 'e'

    for h, m in zip(hours, [m1, m2, m3, m4, m5]):
        now = now.add(hours=h)
        logger.debug(m)

    assert file_1.read() == m5 + '\n'
    assert file_2.read() == m4 + '\n'
    assert file_3.read() == m2 + '\n' + m3 + '\n'
    assert file_4.read() == m1 + '\n'

@pytest.mark.parametrize('backups', ['1 hour', '1H', ' 1 h ', datetime.timedelta(hours=1), pendulum.Interval(hours=1.0)])
def test_backups_time(monkeypatch_now, tmpdir, logger, backups):
    monkeypatch_now(lambda *a, **k: pendulum.now().add(hours=23))

    file = tmpdir.join('test.log')

    file.write('0')
    for i in range(1, 4):
        tmpdir.join('test.log.%d' % i).write('%d' % i)

    logger.start(file.realpath(), rotation=0, backups=backups, format='{message}')
    logger.debug("test")

    assert len(tmpdir.listdir()) == 1
    assert file.read() == 'test\n'

@pytest.mark.parametrize('backups', [0, 1, 9, 10, 11, 50, None])
def test_backups_count(tmpdir, logger, backups):
    log_count = 10
    files_checked = set()

    logger.start(tmpdir.join('test.log'), rotation=0, backups=backups, format='{message}')

    for i in range(log_count):
        logger.debug(str(i))

    if backups is None or backups >= log_count:
        max_num = log_count
    else:
        max_num = backups

    for i in range(max_num + 1):
        if i == 0:
            file_name = 'test.log'
        else:
            z = len(str(max_num))
            file_name = 'test.log.%s' % str(i).zfill(z)

        if i == log_count:
            expected = ''
        else:
            expected = str(log_count - 1 - i) + '\n'

        file = tmpdir.join(file_name)
        assert file.read() == expected
        files_checked.add(file)

    for f in tmpdir.listdir():
        assert f in files_checked

def test_backups_function(tmpdir, logger):
    logger.start(tmpdir.join('test.log'), rotation=0, backups=lambda logs: logs, format='{message}')

    tmpdir.join('test.log.123').write('')

    for i in range(15):
        logger.debug(str(i))
        assert len(tmpdir.listdir()) == 1
        assert tmpdir.join('test.log').read() == '%d\n' % i

def test_backups_at_initialization(tmpdir, logger):
    for i in reversed(range(1, 10)):
        tmpdir.join('test.log.%d' % i).write(str(i))

    logger.start(tmpdir.join('test.log'), backups=1)

    assert len(tmpdir.listdir()) == 2
    assert tmpdir.join('test.log').read() == ''
    assert tmpdir.join('test.log.1').read() == '1'

@pytest.mark.parametrize('previous', [1, 5, 9, 20])
def test_backups_with_previous_files(tmpdir, logger, previous):
    log_count = 5
    backups = 9
    files_checked = set()

    for i in reversed(range(previous)):
        if i == 0:
            file_name = 'test.log'
        else:
            z = len(str(previous))
            file_name = 'test.log.%s' % str(i).zfill(z)
        file = tmpdir.join(file_name)
        file.write('previous %d' % i)

    logger.start(tmpdir.join('test.log'), rotation=0, backups=backups, format='{message}')

    for i in range(log_count):
        logger.debug(str(i))

    for i in range(log_count):
        file_name = 'test.log' + ('.%d' % i if i else '')
        file = tmpdir.join(file_name)
        expected = str(log_count - 1 - i) + '\n'
        assert file.read() == expected
        files_checked.add(file)

    max_num = min(backups, log_count + previous - 1)

    for i in range(log_count, max_num + 1):
        j = i - log_count
        expected = 'previous %d' % j
        file_name = 'test.log.%d' % i
        file = tmpdir.join('test.log.%d' % i)
        assert file.read() == expected
        files_checked.add(file)

    for f in tmpdir.listdir():
        assert f in files_checked

def test_backups_with_other_files(tmpdir, logger):
    log_count = 9
    files_checked = set()

    others = ['test_.log', 'tes.log', 'test.out', 'test.logg', 'atest.log', 'test.log.nope', 'test']
    for other in others:
        tmpdir.join(other).write(other)

    logger.start(tmpdir.join('test.log'), rotation=0, backups=None, format='{message}')

    for i in range(log_count):
        logger.debug(str(i))

    for i in range(log_count + 1):
        file_name = 'test.log' + ('.%d' % i if i else '')
        expected = (str(log_count - 1 - i) + '\n') if i != log_count else ''
        file = tmpdir.join(file_name)
        assert file.read() == expected
        files_checked.add(file)

    for other in others:
        file = tmpdir.join(other)
        assert file.read() == other
        files_checked.add(file)

    for f in tmpdir.listdir():
        assert f in files_checked

def test_backups_zfill(tmpdir, logger):
    logger.start(tmpdir.join('test.log'), rotation=0, backups=None, format='{message}')

    logger.debug('a')
    logger.debug('0')
    assert tmpdir.join('test.log.1').read() == 'a\n'

    for _ in range(10):
        logger.debug('0')

    logger.debug('b')
    logger.debug('0')
    assert tmpdir.join('test.log.01').read() == 'b\n'

    for _ in range(100):
        logger.debug('0')

    logger.debug('c')
    logger.debug('0')
    assert tmpdir.join('test.log.001').read() == 'c\n'

    assert tmpdir.join('test.log.103').read() == 'b\n'
    assert tmpdir.join('test.log.115').read() == 'a\n'
    assert tmpdir.join('test.log.116').read() == ''
    assert tmpdir.join('test.log.117').check(exists=0)


@pytest.mark.parametrize('mode', ['a', 'w'])
@pytest.mark.parametrize('backups', [10, None])
def test_mode(tmpdir, logger, mode, backups):
    file = tmpdir.join('test.log')
    file.write('a')
    logger.start(file.realpath(), rotation=10, backups=backups, format='{message}', mode=mode)
    logger.debug('b')
    logger.debug('c' * 10)

    assert tmpdir.join('test.log').read() == 'c' * 10 + '\n'
    assert tmpdir.join('test.log.1').read() == 'a' * (mode == 'a') + 'b\n'

@pytest.mark.parametrize('compression', ['gz', 'gzip', 'BZ2', 'bzip2', 'zip', 'XZ', 'lzma'])
def test_compression(tmpdir, logger, compression):
    logger.start(tmpdir.join('test.log'), rotation=0, compression=compression, format='{message}')
    logger.debug('a')

    assert tmpdir.join('test.log.1.%s' % compression).check(exists=1)
    assert tmpdir.join('test.log').read() == 'a\n'

def test_compression_function(tmpdir, logger):
    def compress(file):
        os.replace(file, file + '.custom_compression')
    logger.start(tmpdir.join('test.log'), rotation='10 B', compression=compress, format='{message}')
    logger.debug('abc')
    logger.debug('d' * 10)

    assert len(tmpdir.listdir()) == 2
    assert tmpdir.join('test.log').read() == 'd' * 10 + '\n'
    assert tmpdir.join('test.log.1.custom_compression').read() == 'abc\n'

def test_compression_rotation(tmpdir, logger):
    import gzip
    n = logger.start(tmpdir.join('test.log'), rotation=0, compression=True, format='{message}', backups=5)

    for i in range(10):
        logger.debug(str(i))
    logger.stop(n)

    assert tmpdir.join('test.log').read() == '9\n'

    for i in range(5):
        archive = tmpdir.join('test.log.%d.gz' % (i + 1))
        with gzip.open(archive.realpath()) as gz:
            assert gz.read() == b'%d\n' % (9 - i - 1)

def test_compression_without_rotation(tmpdir, logger):
    import gzip
    n = logger.start(tmpdir.join('test.log'), compression=True, format='{message}')
    logger.debug("Test")
    logger.stop(n)

    assert len(tmpdir.listdir()) == 1
    archive = tmpdir.join('test.log.gz')
    with gzip.open(archive.realpath()) as gz:
        assert gz.read() == b'Test\n'

def test_compression_backup_file_exists(tmpdir, logger):
    import gzip
    tmpdir.join('test_1.log').write('not compressed')
    logger.start(tmpdir.join('test_{n}.log'), compression=True, format='{message}', rotation='10 B')
    logger.debug('a')
    logger.debug('b' * 10)

    assert len(tmpdir.listdir()) == 3
    assert tmpdir.join('test_1.log').read() == 'b' * 10 + '\n'
    assert tmpdir.join('test_1.log.1').read() == 'not compressed'
    with gzip.open(tmpdir.join('test_0.log.gz').realpath()) as gz:
        assert gz.read() == b'a\n'

def test_compression_0_backups(tmpdir, logger):
    logger.start(tmpdir.join('test.log'), compression=True, rotation=0, backups=0, format='{message}')

    for m in ['a', 'b']:
        logger.debug(m)
        assert len(tmpdir.listdir()) == 1
        assert tmpdir.join('test.log').read() == m + '\n'

@pytest.mark.parametrize('rotate', [True, False])
def test_compression_atexit(tmpdir, logger, rotate, pyexec):
    import gzip

    file_log = tmpdir.join("test.log")
    file_gz = tmpdir.join("test.log.gz")

    start = str(file_log.realpath())
    rotation = '50' if rotate else 'None'

    code = ('logger.start("' + start + '", format="{message}", compression="gz", rotation=' + rotation + ')\n'
            'logger.info("It works.")')

    pyexec(code, True)

    if rotate:
        assert file_gz.check(exists=0)
        assert file_log.read() == "It works.\n"
    else:
        assert file_log.check(exists=0)
        with gzip.open(file_gz.realpath()) as gz:
            assert gz.read() == b'It works.\n'

@pytest.mark.parametrize('rotation', [
    "w7", "w10", "w-1", "h", "M",
    "w1at13", "www", "13 at w2",
    "K", "tufy MB", "111.111.111 kb", "3 Ki",
    "2017.11.12", "11:99", "monday at 2017",
    "e days", "2 days 8 pouooi", "foobar",
    object(), os, pendulum.Date(2017, 11, 11), pendulum.now(), 1j,
])
def test_invalid_rotation(logger, rotation):
    with pytest.raises(ValueError):
        logger.start('test.log', rotation=rotation)

@pytest.mark.parametrize('backups', [
    "W5", "monday at 14:00", "sunday", "nope",
    "5 MB", "3 hours 2 dayz", "d", "H",
    datetime.time(12, 12, 12), os, object(),
])
def test_invalid_backups(logger, backups):
    with pytest.raises(ValueError):
        logger.start('test.log', backups=backups)

@pytest.mark.parametrize('compression', ['.tar.gz', 0, 1, os, object(), {"zip"}, "rar", ".7z"])
def test_invalid_compression(logger, compression):
    with pytest.raises(ValueError):
        logger.start('test.log', compression=compression)
