# coding: utf-8

import pytest
import pendulum
import datetime
import os
from loguru import logger


@pytest.mark.parametrize('backups', ['1 hour', '1H', ' 1 h ', datetime.timedelta(hours=1), pendulum.Interval(hours=1.0)])
def test_backups_time(monkeypatch_now, tmpdir, backups):
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
def test_backups_count(tmpdir, backups):
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

def test_backups_function(tmpdir):
    logger.start(tmpdir.join('test.log'), rotation=0, backups=lambda logs: logs, format='{message}')

    tmpdir.join('test.log.123').write('')

    for i in range(15):
        logger.debug(str(i))
        assert len(tmpdir.listdir()) == 1
        assert tmpdir.join('test.log').read() == '%d\n' % i

def test_backups_at_initialization(tmpdir):
    for i in reversed(range(1, 10)):
        tmpdir.join('test.log.%d' % i).write(str(i))

    logger.start(tmpdir.join('test.log'), backups=1)

    assert len(tmpdir.listdir()) == 2
    assert tmpdir.join('test.log').read() == ''
    assert tmpdir.join('test.log.1').read() == '1'

@pytest.mark.parametrize('previous', [1, 5, 9, 20])
def test_backups_with_previous_files(tmpdir, previous):
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

def test_backups_with_other_files(tmpdir):
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

def test_backups_zfill(tmpdir):
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
def test_mode(tmpdir, mode, backups):
    file = tmpdir.join('test.log')
    file.write('a')
    logger.start(file.realpath(), rotation=10, backups=backups, format='{message}', mode=mode)
    logger.debug('b')
    logger.debug('c' * 10)

    assert tmpdir.join('test.log').read() == 'c' * 10 + '\n'
    assert tmpdir.join('test.log.1').read() == 'a' * (mode == 'a') + 'b\n'

@pytest.mark.parametrize('backups', [
    "W5", "monday at 14:00", "sunday", "nope",
    "5 MB", "3 hours 2 dayz", "d", "H",
    datetime.time(12, 12, 12), os, object(),
])
def test_invalid_backups(backups):
    with pytest.raises(ValueError):
        logger.start('test.log', backups=backups)
