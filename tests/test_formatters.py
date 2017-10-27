# coding: utf-8

import re
import loguru
import pytest

@pytest.mark.parametrize('format, validator', [
    ('{message}', lambda r: r == 'Message'),
    ('{name}', lambda r: r == 'tests.test_formatters'),
    ('{time}', lambda r: re.fullmatch(r'\d+-\d+-\d+T\d+:\d+:\d+[.,]\d+[+-]\d+:\d+', r)),
    ('{time:HH[h] mm[m] ss[s]}', lambda r: re.fullmatch(r'\d+h \d+m \d+s', r)),
    ('{time:HH}x{time:mm}x{time:ss}', lambda r: re.fullmatch(r'\d+x\d+x\d+', r)),
    ('{time.int_timestamp}', lambda r: re.fullmatch(r'\d+', r)),
    ('{elapsed}', lambda r: re.fullmatch(r'(\s*([\d.]+) ([a-zA-Z]+)\s*)+', r)),
    ('{elapsed.seconds}', lambda r: re.fullmatch(r'\d+', r)),
    ('{line}', lambda r: re.fullmatch(r'\d+', r)),
    ('{level}', lambda r: r == 'DEBUG'),
    ('{level.name}', lambda r: r == 'DEBUG'),
    ('{level.no}', lambda r: r == str(loguru.DEBUG)),
    ('{file}', lambda r: r == 'test_formatters.py'),
    ('{file.name}', lambda r: r == 'test_formatters.py'),
    ('{file.path}', lambda r: r.endswith('test_formatters.py')),
    ('{function}', lambda r: r == 'test_log_formatters'),
    ('{module}', lambda r: r == 'test_formatters'),
    ('{thread}', lambda r: re.fullmatch(r'\d+', r)),
    ('{thread.id}', lambda r: re.fullmatch(r'\d+', r)),
    ('{thread.name}', lambda r: isinstance(r, str) and r != ""),
    ('{process}', lambda r: re.fullmatch(r'\d+', r)),
    ('{process.id}', lambda r: re.fullmatch(r'\d+', r)),
    ('{process.name}', lambda r: isinstance(r, str) and r != ""),
    ('%s {message} %d', lambda r: r == '%s Message %d'),
    ('{{a}} {message} {{1}}', lambda r: r == '{a} Message {1}'),
    ('天 {message} 天', lambda r: r == '天 Message 天'),
])
def test_log_formatters(format, validator, logger, writer):
    logger.log_to(writer, format=format)
    logger.debug("Message")
    result = writer.read().rstrip('\n')
    assert validator(result)

@pytest.mark.parametrize('format, validator', [
    ('{time}.log', lambda r: re.fullmatch(r'\d+-\d+-\d+_\d+-\d+-\d+\.log', r)),
    ('{time:HH[h] mm[m] ss[s]}.log', lambda r: re.fullmatch(r'\d+h \d+m \d+s\.log', r)),
    ('{time:HH}x{time:mm}x{time:ss}.log', lambda r: re.fullmatch(r'\d+x\d+x\d+\.log', r)),
    ('{start_time}.out', lambda r: re.fullmatch(r'\d+-\d+-\d+_\d+-\d+-\d+\.out', r)),
    ('{start_time:HH[h] mm[m] ss[s]}.out', lambda r: re.fullmatch(r'\d+h \d+m \d+s\.out', r)),
    ('{start_time:HH}x{time:mm}x{time:ss}.out', lambda r: re.fullmatch(r'\d+x\d+x\d+\.out', r)),
    ('{rotation_time}', lambda r: r == 'None'),
    ('{n}', lambda r: r == '0'),
    ('{n: <2}', lambda r: r == '0 '),
    ('{n+1}', lambda r: r == '1'),
    ('{n+1:0>2}', lambda r: r == '01'),
    ('%s_{n}_%d', lambda r: r == '%s_0_%d'),
    ('{{a}}_{n}_{{1}}', lambda r: r == '{a}_0_{1}'),
    ('天_{n}_天', lambda r: r == '天_0_天'),
])
@pytest.mark.parametrize('part', ["file", "dir", "both"])
def test_file_formatters(tmpdir, format, validator, part, logger):
    if part == "file":
        file = tmpdir.join(format)
    elif part == "dir":
        file = tmpdir.join(format, 'log.log')
    elif part == "both":
        file = tmpdir.join(format, format)

    logger.log_to(file.realpath())
    logger.debug("Message")

    files = [f for f in tmpdir.visit() if f.check(file=1)]

    assert len(files) == 1

    file = files[0]

    if part == 'file':
        assert validator(file.basename)
    elif part == 'dir':
        assert file.basename == 'log.log'
        assert validator(file.dirpath().basename)
    elif part == 'both':
        assert validator(file.basename)
        assert validator(file.dirpath().basename)
