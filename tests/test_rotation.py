# coding: utf-8

import pytest
import pendulum
import loguru
from datetime import time, timedelta
import math
import os
import re

def sort_files_by_num(test_log, directory):
    files = [f for f in directory.listdir() if re.fullmatch(re.escape(test_log) + '\.\d+', f.basename)]
    return sorted(files, key=lambda f: int(f.basename.split('.')[-1]))

@pytest.mark.parametrize('name, should_rename', [
    ('test.log', True),
    ('{n}.log', False),
    ('{start_time}.log', True),
    ('test.log.{n+1}', False),
    ('test.log.1', True),
])
def test_renaming(tmpdir, logger, name, should_rename):
    file = tmpdir.join(name)
    logger.log_to(file.realpath(), size=0)

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
    8, 8.0, 7.99, "8", "8 B", "8e-6MB", "0.008 kiB", "64b", lambda f, m: "c" not in m
])
def test_size(tmpdir, logger, size):
    file_1 = tmpdir.join("test.log")
    file_2 = tmpdir.join("test.log.1")
    file_3 = tmpdir.join("test.log.2")
    file_4 = tmpdir.join("test.log.3")
    logger.log_to(file_1.realpath(), format='{message}', size=size)

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
    ('13:00:00.1234567890987654321', [0.9, 2, 10, 15, 256]),
    ('w0', [11, 1, 24 * 7 - 1, 1, 24 * 7]),
    ('W0 00:00', [10, 24 * 7 - 5, 0.1, 24 * 30, 24 * 14]),
    ('W6', [24, 24 * 28, 24 * 5, 24, 364 * 24]),
    ('w6 00', [8, 24 * 7, 24 * 6, 24, 24 * 8]),
    ('13 W6', [0.5, 1, 24 * 6, 24 * 6, 365 * 24]),
    ('11:00:00 w2', [48 + 22, 3, 24 * 6, 24, 366 * 24]),
    (time(15), [2, 3, 19, 5, 24]),
    (lambda at, now: now.add(months=1).start_of('month').at(12, 0, 0), [24 * 12, 24, 24 * 30, 25 * 60, 365 * 24]),
    (lambda at, now: at.add(days=1) if at else now.add(days=1).at(12, 0, 0), [23, 1, 23, 1, 24]),
    ("2 h", [1, 2, 0.9, 0.5, 10]),
    ("1 hour", [0.5, 1, 0.1, 100, 1000]),
    ("7 days", [24 * 7 - 1, 1, 48, 24 * 10, 24 * 365]),
    ("1h 30 minutes", [1.4, 0.2, 1, 2, 10]),
    ("1 w, 2D", [24 * 8, 24 * 2, 24, 24 * 9, 24 * 9]),
    ("mo", [24 * 29, 24 * 7, 0, 24 * 25, 24 * 300]),
    ("d", [23, 23, 1, 48, 24]),
    ("1.5d", [30, 10, 0.9, 48, 35]),
    ("1.222 hours, 3.44s", [1.222, 0.1, 1, 1.2, 2]),
    (timedelta(hours=1), [0.9, 0.2, 0.7, 0.5, 3]),
])
def test_when(monkeypatch, tmpdir, when, hours, logger):
    now = pendulum.parse("2017-06-18 12:00:00")  # Sunday

    monkeypatch.setattr(loguru, 'now', lambda *a, **k: now)

    file_1 = tmpdir.join("test.log")
    file_2 = tmpdir.join("test.log.1")
    file_3 = tmpdir.join("test.log.2")
    file_4 = tmpdir.join("test.log.3")

    logger.log_to(file_1.realpath(), format='{message}', when=when)

    m1, m2, m3, m4, m5 = 'a', 'b', 'c', 'd', 'e'

    for h, m in zip(hours, [m1, m2, m3, m4, m5]):
        now = now.add(hours=h)
        logger.debug(m)

    assert file_1.read() == m5 + '\n'
    assert file_2.read() == m4 + '\n'
    assert file_3.read() == m2 + '\n' + m3 + '\n'
    assert file_4.read() == m1 + '\n'

@pytest.mark.parametrize('backups', [0, 1, 9, 10, 11, 50, math.inf])
def test_backups_count(tmpdir, logger, backups):
    log_count = 10
    files_checked = set()

    it = iter([False] + [True] * log_count)

    file = tmpdir.join('test.log')
    logger.log_to(file.realpath(), size=lambda *a, **k: next(it), backups=backups, format='{message}')

    for i in range(1, log_count + 1):
        logger.debug(str(i))

    assert file.read() == '%d\n' % log_count
    files_checked.add(file)

    files = sort_files_by_num('test.log', tmpdir)

    for i in range(min(backups, log_count - 1)):
        file = files[i]
        assert file.read() == '%d\n' % (log_count - i - 1)
        files_checked.add(file)

    for f in tmpdir.listdir():
        assert f in files_checked

@pytest.mark.parametrize('backups', ['1 hour', '1H', 'h', timedelta(hours=1)])
def test_backups_time(monkeypatch, tmpdir, logger, backups):
    monkeypatch.setattr(loguru, 'now', lambda *a, **k: pendulum.now().add(hours=23))

    file = tmpdir.join('test.log')

    file.write('0')
    for i in range(1, 4):
        tmpdir.join('test.log.%d' % i).write('%d' % i)

    logger.log_to(file.realpath(), size=0, backups=backups, format='{message}')
    logger.debug("test")

    assert len(tmpdir.listdir()) == 1
    assert file.read() == 'test\n'

@pytest.mark.parametrize('backups', [0, 1, 9, 10, 11, 50, math.inf])
def test_backups_with_other_files(tmpdir, logger, backups):
    log_count = 10
    previous_count = 10
    files_checked = set()

    # Not related files should not be deleted
    others = ['test_.log', 'tes.log', 'test.out', 'test.logg', 'atest.log', 'test.log.nope', 'test']
    for other in others:
        tmpdir.join(other).write(other)

    file = tmpdir.join('test.log')

    # Files from previous session sould be deleted if more than backups
    for i in reversed(range(1, previous_count + 1)):
        tmpdir.join('test.log.%d' % i).write('previous %d' % i)
    file.write('previous 0')

    logger.log_to(file.realpath(), size=0, backups=backups, format='{message}')

    for i in range(1, log_count + 1):
        logger.debug(str(i))

    assert file.read() == '%d\n' % log_count
    files_checked.add(file)

    files = sort_files_by_num('test.log', tmpdir)

    last = min(backups, log_count - 1)
    for i in range(last):
        file = files[i]
        assert file.read() == '%d\n' % (log_count - i - 1)
        files_checked.add(file)

    if backups >= log_count:
        remaining_backups = backups - log_count
        remaining_backups = min(remaining_backups, previous_count)
        for i in range(last, last + 1 + remaining_backups):
            file = files[i]
            assert file.read() == 'previous %d' % (i - last)
            files_checked.add(file)

    for other in others:
        file = tmpdir.join(other)
        assert file.read() == other
        files_checked.add(file)

    for f in tmpdir.listdir():
        assert f in files_checked

def test_backups_zfill(tmpdir, logger):
    it = iter([False] + [True]*120)
    logger.log_to(tmpdir.join('test.log'), size=lambda *a, **k: next(it), backups=float('inf'), format='{message}')

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

    files = sort_files_by_num('test.log', tmpdir)
    assert len(files) == 10 + 100 + 2 * 3 - 1
    assert files[-1].basename == 'test.log.%d' % len(files)
    assert files[-1].read() == 'a\n'

@pytest.mark.parametrize('mode', ['a', 'w'])
def test_mode(tmpdir, logger, mode):
    file = tmpdir.join('test.log')
    file.write('a')
    it = iter([False, True])
    logger.log_to(file.realpath(), size=lambda *a, **k: next(it), format='{message}', mode=mode)
    logger.debug('b')
    logger.debug('c')

    assert tmpdir.join('test.log').read() == 'c\n'
    assert tmpdir.join('test.log.1').read() == 'a' * (mode == 'a') + 'b\n'
