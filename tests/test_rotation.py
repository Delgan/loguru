# coding: utf-8

import pytest
import pendulum
import loguru
import datetime
import math
import os
import re


@pytest.mark.parametrize('name, should_rename', [
    ('test.log', True),
    ('{n}.log', False),
    ('{start_time}.log', True),
    ('test.log.{n+1}', False),
    ('test.log.1', True),
])
def test_renaming(tmpdir, logger, name, should_rename):
    file = tmpdir.join(name)
    logger.log_to(file.realpath(), rotation=0)

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
    logger.log_to(file_1.realpath(), format='{message}', rotation=size)

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
    ("mo", [24 * 29, 24 * 7, 0, 24 * 25, 24 * 300]),
    ("d", [23, 23, 1, 48, 24]),
    ("1.5d", [30, 10, 0.9, 48, 35]),
    ("1.222 hours, 3.44s", [1.222, 0.1, 1, 1.2, 2]),
    (datetime.timedelta(hours=1), [0.9, 0.2, 0.7, 0.5, 3]),
    (pendulum.Interval(minutes=30), [0.48, 0.04, 0.07, 0.44, 0.5]),
])
def test_time_rotation(monkeypatch, tmpdir, when, hours, logger):
    now = pendulum.parse("2017-06-18 12:00:00")  # Sunday

    monkeypatch.setattr(loguru, 'now', lambda *a, **k: now)

    file_1 = tmpdir.join("test.log")
    file_2 = tmpdir.join("test.log.1")
    file_3 = tmpdir.join("test.log.2")
    file_4 = tmpdir.join("test.log.3")

    logger.log_to(file_1.realpath(), format='{message}', rotation=when)

    m1, m2, m3, m4, m5 = 'a', 'b', 'c', 'd', 'e'

    for h, m in zip(hours, [m1, m2, m3, m4, m5]):
        now = now.add(hours=h)
        logger.debug(m)

    assert file_1.read() == m5 + '\n'
    assert file_2.read() == m4 + '\n'
    assert file_3.read() == m2 + '\n' + m3 + '\n'
    assert file_4.read() == m1 + '\n'

@pytest.mark.parametrize('backups', ['1 hour', '1H', 'h', datetime.timedelta(hours=1), pendulum.Interval(hours=1.0)])
def test_backups_time(monkeypatch, tmpdir, logger, backups):
    monkeypatch.setattr(loguru, 'now', lambda *a, **k: pendulum.now().add(hours=23))

    file = tmpdir.join('test.log')

    file.write('0')
    for i in range(1, 4):
        tmpdir.join('test.log.%d' % i).write('%d' % i)

    logger.log_to(file.realpath(), rotation=0, backups=backups, format='{message}')
    logger.debug("test")

    assert len(tmpdir.listdir()) == 1
    assert file.read() == 'test\n'

@pytest.mark.parametrize('backups', [0, 1, 9, 10, 11, 50, None])
def test_backups_count(tmpdir, logger, backups):
    log_count = 10
    files_checked = set()

    logger.log_to(tmpdir.join('test.log'), rotation=0, backups=backups, format='{message}')

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
    logger.log_to(tmpdir.join('test.log'), rotation=0, backups=lambda logs: logs, format='{message}')

    tmpdir.join('test.log.123').write('')

    for i in range(15):
        logger.debug(str(i))
        assert len(tmpdir.listdir()) == 1
        assert tmpdir.join('test.log').read() == '%d\n' % i

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

    logger.log_to(tmpdir.join('test.log'), rotation=0, backups=backups, format='{message}')

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

    logger.log_to(tmpdir.join('test.log'), rotation=0, backups=None, format='{message}')

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
    logger.log_to(tmpdir.join('test.log'), rotation=0, backups=None, format='{message}')

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
    logger.log_to(file.realpath(), rotation=10, backups=backups, format='{message}', mode=mode)
    logger.debug('b')
    logger.debug('c' * 10)

    assert tmpdir.join('test.log').read() == 'c' * 10 + '\n'
    assert tmpdir.join('test.log.1').read() == 'a' * (mode == 'a') + 'b\n'

@pytest.mark.parametrize('rotation', [
    "w7", "w10", "w-1",
    "w1at13", "www", "13 at w2",
    "K", "tufy MB", "111.111.111 kb", "3 Ki",
    "2017.11.12", "11:99", "monday at 2017",
    "e days", "2 days 8 pouooi", "foobar",
    object(), os, pendulum.Date(2017, 11, 11), pendulum.now(),
])
def test_invalid_rotation(logger, rotation):
    with pytest.raises(ValueError):
        logger.log_to('test.log', rotation=rotation)

@pytest.mark.parametrize('backups', [
    "W5", "monday at 14:00", "sunday",
    "nope", "5 MB", "3 hours 2 dayz",
    datetime.time(12, 12, 12), os, object(),
])
def test_invalid_backups(logger, backups):
    with pytest.raises(ValueError):
        logger.log_to('test.log', backups=backups)
