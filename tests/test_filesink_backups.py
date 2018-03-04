import pytest
import pendulum
import datetime
import os
from loguru import logger


@pytest.mark.parametrize('backups', ['1 hour', '1H', ' 1 h ', datetime.timedelta(hours=1), pendulum.Interval(hours=1.0)])
def test_backups_time(monkeypatch_now, tmpdir, backups):
    i = logger.start(tmpdir.join('test.log.x'), backups=backups)
    logger.debug("test")
    logger.stop(i)

    assert len(tmpdir.listdir()) == 1

    monkeypatch_now(lambda *a, **k: pendulum.now().add(hours=24))

    i = logger.start(tmpdir.join('test.log'), backups=backups)
    logger.debug("test")

    assert len(tmpdir.listdir()) == 2
    logger.stop(i)
    assert len(tmpdir.listdir()) == 0

@pytest.mark.parametrize('backups', [0, 1, 10])
def test_backups_count(tmpdir, backups):
    file = tmpdir.join('test.log')

    for i in range(backups):
        tmpdir.join('test.log.%d' % i).write('test')

    i = logger.start(file.realpath(), backups=backups)
    logger.debug("test")
    logger.stop(i)

    assert len(tmpdir.listdir()) == backups

@pytest.mark.parametrize('mode', ['all', 'none'])
def test_backups_function(tmpdir, mode):
    func = lambda logs: logs if mode == 'all' else []

    for i in range(10):
        tmpdir.join('test.log.%d' % i).write('')

    i = logger.start(tmpdir.join('test.log'), backups=func)
    logger.stop(i)

    assert len(tmpdir.listdir()) == 0 if mode == 'all' else 10

def test_managed_files(tmpdir):
    others = ['test.log', 'test.log.1', 'test.log.1.gz', 'test.log.rar']

    for other in others:
        tmpdir.join(other).write(other)

    i = logger.start(tmpdir.join('test.log'), backups=0)
    logger.stop(i)

    assert len(tmpdir.listdir()) == 0

def test_not_managed_files(tmpdir):
    others = ['test_.log', '_test.log', 'test', 'tes.log', 'te.st.log', 'test.1.log']

    for other in others:
        tmpdir.join(other).write(other)

    i = logger.start(tmpdir.join('test.log'), backups=0)
    logger.stop(i)

    assert len(tmpdir.listdir()) == len(others)

def test_manage_files_at_rotation(tmpdir):
    tmpdir.join('test.log.1').write('')
    tmpdir.join('test.log.2').write('')
    tmpdir.join('test.log.3').write('')

    logger.start(tmpdir.join('test.log'), backups=1, rotation=0)
    logger.debug("test")

    assert len(tmpdir.listdir()) == 2

def test_no_renaming(tmpdir):
    i = logger.start(tmpdir.join('test.log'), format="{message}", backups=10)
    logger.debug("test")
    logger.stop(i)

    assert len(tmpdir.listdir()) == 1
    assert tmpdir.join('test.log').read() == 'test\n'

@pytest.mark.parametrize('backups', [
    "W5", "monday at 14:00", "sunday", "nope",
    "5 MB", "3 hours 2 dayz", "d", "H",
    datetime.time(12, 12, 12), os, object(),
])
def test_invalid_backups(backups):
    with pytest.raises(ValueError):
        logger.start('test.log', backups=backups)
