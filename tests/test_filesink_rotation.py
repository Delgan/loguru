import pytest
import pendulum
import datetime
import os
import re
from loguru import logger


@pytest.mark.parametrize('name, should_rename', [
    ('test.log', True),
    ('{n}.log', False),
    ('{start_time}.log', True),
    ('test.log.{n}', False),
    ('test.log.1', True),
])
def test_renaming(tmpdir, name, should_rename):
    file = tmpdir.join(name)
    i = logger.start(file, format="{message}", rotation="10 B")

    assert len(tmpdir.listdir()) == 1
    root, ext = os.path.splitext(str(tmpdir.listdir()[0]))
    reg = re.escape(root) + r'\.[A-Z0-9]+' + re.escape(ext)

    logger.debug("aaaaaaa")
    logger.debug("bbbbbbb")
    logger.debug("ccccccc")

    renamed = sum(re.match(reg, str(f.realpath())) is not None for f in tmpdir.listdir())

    if should_rename:
        assert renamed == len(tmpdir.listdir()) - 1
    else:
        assert renamed == 0

    assert len(tmpdir.listdir()) == 3
    assert {f.read() for f in tmpdir.listdir()} == {'aaaaaaa\n', 'bbbbbbb\n', 'ccccccc\n'}

@pytest.mark.parametrize('size', [
    8, 8.0, 7.99, "8 B", "8e-6MB", "0.008 kiB", "64b"
])
def test_size_rotation(tmpdir, size):
    file = tmpdir.join("test.log")
    i = logger.start(file.realpath(), format='{message}', rotation=size)

    logger.debug("abcde")
    logger.debug("fghij")
    logger.debug("klmno")

    logger.stop(i)

    assert len(tmpdir.listdir()) == 3
    assert {f.read() for f in tmpdir.listdir()} == {'abcde\n', 'fghij\n', 'klmno\n'}

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
    ('hourly', [0.9, 0.2, 0.8, 3, 1]),
    ('daily', [11, 1, 23, 1, 24]),
    ('WEEKLY', [11, 2, 24 * 6, 24, 24 * 7]),
    (' mOnthLY', [0, 24 * 13, 29 * 24, 60 * 24, 24 * 35]),
    ('yearly ', [100, 24 * 7 * 30, 24 * 300, 24 * 100, 24 * 400]),
])
def test_time_rotation(monkeypatch_now, tmpdir, when, hours):
    now = pendulum.parse("2017-06-18 12:00:00")  # Sunday

    monkeypatch_now(lambda *a, **k: now)

    i = logger.start(tmpdir.join('test.log').realpath(), format='{message}', rotation=when)

    for h, m in zip(hours, ['a', 'b', 'c', 'd', 'e']):
        now = now.add(hours=h)
        logger.debug(m)

    logger.stop(i)

    assert len(tmpdir.listdir()) == 4
    assert {f.read() for f in tmpdir.listdir()} == {'a\n', 'b\nc\n', 'd\n', 'e\n'}

def test_function_rotation(tmpdir):
    x = iter([False, True, False])
    i = logger.start(tmpdir.join("test.log"), rotation=lambda *_: next(x))
    logger.debug("a")
    assert len(tmpdir.listdir()) == 1
    logger.debug("b")
    assert len(tmpdir.listdir()) == 2
    logger.debug("c")
    assert len(tmpdir.listdir()) == 2

def test_no_rotation_at_stop(tmpdir):
    i = logger.start(tmpdir.join("test.log"), rotation="10 MB")
    logger.debug("test")
    logger.stop(i)

    assert len(tmpdir.listdir()) == 1
    assert tmpdir.join("test.log").check(exists=1)

@pytest.mark.parametrize('rotation', [
    "w7", "w10", "w-1", "h", "M",
    "w1at13", "www", "13 at w2", "w",
    "K", "tufy MB", "111.111.111 kb", "3 Ki",
    "2017.11.12", "11:99", "monday at 2017",
    "e days", "2 days 8 pouooi", "foobar",
    object(), os, pendulum.Date(2017, 11, 11), pendulum.now(), 1j,
])
def test_invalid_rotation(rotation):
    with pytest.raises(ValueError):
        logger.start('test.log', rotation=rotation)


