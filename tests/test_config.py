import sys
import textwrap
import pytest

@pytest.mark.parametrize('config_mode', ['dict', 'file'])
def test_source(logger, capsys, tmpdir, config_mode):
    file = tmpdir.join('test.log')

    if config_mode == 'dict':
        config = {
            'dummy': 4,
            'sinks': [
                {'sink': file.realpath(), 'format': 'FileSink: {message}'},
                {'sink': sys.stdout, 'format': 'StdoutSink: {message}'},
            ]
        }
    elif config_mode == 'file':
        config = tmpdir.join('config.py')
        config.write(textwrap.dedent("""
        import sys

        config = {
            'dummy': 4,
            'sinks': [
                {'sink': '%s', 'format': 'FileSink: {message}'},
                {'sink': sys.stdout, 'format': 'StdoutSink: {message}'},
            ]
        }
        """ % file.realpath()))

    logger.log_to(sys.stderr)
    res = logger.config(config)
    logger.debug('test')

    out, err = capsys.readouterr()

    assert len(res) == 2
    assert file.read() == 'FileSink: test\n'
    assert out == 'StdoutSink: test\n'
    assert err == ''
    assert logger.dummy == 4

def test_sinks(logger, writer):
    sinks = [
        {'sink': writer, 'format': '{message}'}
    ]

    res = logger.config(sinks=sinks)
    logger.debug('test')

    assert len(res) == 1
    assert writer.read() == 'test\n'

def test_dummy(logger):
    res = logger.config(dummy=42)
    assert logger.dummy == 42

def test_kwargs_overriding(logger):
    logger.config({"dummy": 42}, dummy=24)
    assert logger.dummy == 24

@pytest.mark.parametrize('source', [sys, 123, object(), sys.stderr, [{}]])
def test_invalid(logger, source):
    with pytest.raises(ValueError):
        logger.config(source)
