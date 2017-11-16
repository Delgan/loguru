import sys
import textwrap
import pytest

def test_sinks(logger, capsys, tmpdir):
    file = tmpdir.join('test.log')

    config = {
        'sinks': [
            {'sink': file.realpath(), 'format': 'FileSink: {message}'},
            {'sink': sys.stdout, 'format': 'StdoutSink: {message}'},
        ]
    }

    logger.log_to(sys.stderr)
    res = logger.config(config)
    logger.debug('test')
    for sink_id in res:
        logger.clear(sink_id)
    logger.debug("nope")

    out, err = capsys.readouterr()

    assert len(res) == 2
    assert file.read() == 'FileSink: test\n'
    assert out == 'StdoutSink: test\n'
    assert err == ''
