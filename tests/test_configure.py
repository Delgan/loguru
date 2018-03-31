import sys
import pytest
from loguru import logger


def test_sinks(capsys, tmpdir):
    file = tmpdir.join('test.log')

    config = {
        'sinks': [
            {'sink': file.realpath(), 'format': 'FileSink: {message}'},
            {'sink': sys.stdout, 'format': 'StdoutSink: {message}'},
        ]
    }

    logger.start(sys.stderr, format='StderrSink: {message}')
    res = logger.configure(config)
    logger.debug('test')
    for sink_id in res:
        logger.stop(sink_id)
    logger.debug("nope")

    out, err = capsys.readouterr()

    assert len(res) == 2
    assert file.read() == 'FileSink: test\n'
    assert out == 'StdoutSink: test\n'
    assert err == 'StderrSink: test\nStderrSink: nope\n'

def test_levels(writer):
    config = {
        'levels': [
            {'name': 'my_level', 'icon': 'X', 'no': 12},
            {'name': 'DEBUG', 'icon': '!'}
        ]
    }

    logger.level('abc', 11)
    logger.configure(config)
    logger.start(writer, format="{level.no}|{level.name}|{level.icon}|{message}")

    logger.log('my_level', 'test')
    logger.log('abc', 'wow')
    logger.debug('no bug')

    assert writer.read() == '12|my_level|X|test\n11|abc| |wow\n10|DEBUG|!|no bug\n'

def test_extra(writer):
    config = {
        'extra': {
            'a': 1,
            'b': 'c',
        }
    }

    logger.configure({'extra': {"c": 9}})
    logger.configure(config)

    logger.start(writer, format='{extra[a]} | {extra[b]} | {extra[c]}')
    logger.debug("")

    assert writer.read() == "1 | c | 9\n"
