import pytest
import pendulum
import datetime
import os
from loguru import logger


@pytest.mark.parametrize('retention', ['1 hour', '1H', ' 1 h ', datetime.timedelta(hours=1), pendulum.Interval(hours=1.0)])
def test_retention_time(monkeypatch_now, tmpdir, retention):
    i = logger.start(tmpdir.join('test.log.x'), retention=retention)
    logger.debug("test")
    logger.stop(i)

    assert len(tmpdir.listdir()) == 1

    monkeypatch_now(lambda *a, **k: pendulum.now().add(hours=24))

    i = logger.start(tmpdir.join('test.log'), retention=retention)
    logger.debug("test")

    assert len(tmpdir.listdir()) == 2
    logger.stop(i)
    assert len(tmpdir.listdir()) == 0

@pytest.mark.parametrize('retention', [0, 1, 10])
def test_retention_count(tmpdir, retention):
    file = tmpdir.join('test.log')

    for i in range(retention):
        tmpdir.join('test.log.%d' % i).write('test')

    i = logger.start(file.realpath(), retention=retention)
    logger.debug("test")
    logger.stop(i)

    assert len(tmpdir.listdir()) == retention

def test_retention_function(tmpdir):
    def func(logs):
        for log in logs:
            os.rename(log, log + '.xyz')

    tmpdir.join('test.log.1').write('')
    tmpdir.join('test').write('')

    i = logger.start(tmpdir.join('test.log'), retention=func)
    logger.stop(i)

    assert len(tmpdir.listdir()) == 3
    assert tmpdir.join('test.log.1.xyz').check(exists=1)
    assert tmpdir.join('test.log.xyz').check(exists=1)
    assert tmpdir.join('test').check(exists=1)

def test_managed_files(tmpdir):
    others = ['test.log', 'test.log.1', 'test.log.1.gz', 'test.log.rar', 'test.1.log']

    for other in others:
        tmpdir.join(other).write(other)

    i = logger.start(tmpdir.join('test.log'), retention=0)
    logger.stop(i)

    assert len(tmpdir.listdir()) == 0

def test_not_managed_files(tmpdir):
    others = ['test_.log', '_test.log', 'tes.log', 'te.st.log', 'testlog', 'test']

    for other in others:
        tmpdir.join(other).write(other)

    i = logger.start(tmpdir.join('test.log'), retention=0)
    logger.stop(i)

    assert len(tmpdir.listdir()) == len(others)

def test_manage_formatted_files(tmpdir):
    f1 = tmpdir.join('temp/1/file.log')
    f2 = tmpdir.join('temp/file1.log')
    f3 = tmpdir.join('temp/d1/f1.1.log')

    a = logger.start(tmpdir.join('temp/{n}/file.log'), retention=0)
    b = logger.start(tmpdir.join('temp/file{n}.log'), retention=0)
    c = logger.start(tmpdir.join('temp/d{n}/f{n}.{n}.log'), retention=0)

    logger.debug("test")

    assert f1.check(exists=1)
    assert f2.check(exists=1)
    assert f3.check(exists=1)

    logger.stop(a)
    logger.stop(b)
    logger.stop(c)

    assert f1.check(exists=0)
    assert f2.check(exists=0)
    assert f3.check(exists=0)

def test_manage_file_without_extension(tmpdir):
    file = tmpdir.join('file')

    i = logger.start(file, retention=0)
    logger.debug("?")

    assert len(tmpdir.listdir()) == 1
    assert file.check(exists=1)
    logger.stop(i)
    assert len(tmpdir.listdir()) == 0
    assert file.check(exists=0)

def test_manage_formatted_files_without_extension(tmpdir):
    tmpdir.join('file_8').write("")
    tmpdir.join('file_7').write("")
    tmpdir.join('file_6').write("")

    i = logger.start(tmpdir.join('file_{n}'), retention=0)
    logger.debug("1")
    logger.stop(i)

    assert len(tmpdir.listdir()) == 0

def test_manage_files_at_rotation(tmpdir):
    tmpdir.join('test.log.1').write('')
    tmpdir.join('test.log.2').write('')
    tmpdir.join('test.log.3').write('')

    logger.start(tmpdir.join('test.log'), retention=1, rotation=0)
    logger.debug("test")

    assert len(tmpdir.listdir()) == 2

def test_no_retention_at_stop(tmpdir):
    i = logger.start(tmpdir.join('file.log'), retention=0, process_at_stop=False)
    logger.debug("1")
    logger.stop(i)

    assert len(tmpdir.listdir()) == 1
    assert tmpdir.join('file.log').check(exists=1)

def test_no_renaming(tmpdir):
    i = logger.start(tmpdir.join('test.log'), format="{message}", retention=10)
    logger.debug("test")
    logger.stop(i)

    assert len(tmpdir.listdir()) == 1
    assert tmpdir.join('test.log').read() == 'test\n'

@pytest.mark.parametrize('retention', [
    "W5", "monday at 14:00", "sunday", "nope",
    "5 MB", "3 hours 2 dayz", "d", "H",
    datetime.time(12, 12, 12), os, object(),
])
def test_invalid_retention(retention):
    with pytest.raises(ValueError):
        logger.start('test.log', retention=retention)
