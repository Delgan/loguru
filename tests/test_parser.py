import pytest
import random
import re
import pathlib
import io

import pendulum

from loguru import parser

TEXT = "This\nIs\nRandom\nText\n123456789\nABC!DEF\nThis Is The End\n"

@pytest.fixture
def fileobj():
    with io.StringIO(TEXT) as file:
        yield file

def test_parse_file(tmpdir):
    file = tmpdir.join('test.log')
    file.write(TEXT)
    result, *_ = list(parser.parse(file.realpath(), r"(?P<num>\d+)"))
    assert result == dict(num="123456789")

def test_parse_fileobj(tmpdir):
    file = tmpdir.join('test.log')
    file.write(TEXT)
    result, *_ = list(parser.parse(open(file.realpath()), r"^(?P<t>\w+)"))
    assert result == dict(t="This")

def test_parse_pathlib(tmpdir):
    file = tmpdir.join('test.log')
    file.write(TEXT)
    result, *_ = list(parser.parse(pathlib.Path(file.realpath()), r"(?P<r>Random)"))
    assert result == dict(r="Random")

def test_parse_string_pattern(fileobj):
    result, *_ = list(parser.parse(fileobj, r"(?P<num>\d+)"))
    assert result == dict(num="123456789")

def test_parse_regex_pattern(fileobj):
    regex = re.compile(r"(?P<maj>[a-z]*![a-z]*)", flags=re.I)
    result, *_ = list(parser.parse(fileobj, regex))
    assert result == dict(maj="ABC!DEF")

def test_parse_multiline_pattern(fileobj):
    result, *_ = list(parser.parse(fileobj, r"(?P<text>This[\s\S]*Text\n)"))
    assert result == dict(text="This\nIs\nRandom\nText\n")

def test_parse_without_group(fileobj):
    result, *_ = list(parser.parse(fileobj, r"\d+"))
    assert result == {}

def test_parse_bytes():
    with io.BytesIO(b"Testing bytes!") as fileobj:
        result, *_ = list(parser.parse(fileobj, br"(?P<ponct>[?!:])"))
    assert result == dict(ponct=b"!")

@pytest.mark.parametrize("chunk", [-1, 1, 2**16])
def test_chunk(fileobj, chunk):
    result, *_ = list(parser.parse(fileobj, r"(?P<a>[ABC]+)", chunk=chunk))
    assert result == dict(a="ABC")

def test_positive_lookbehind_pattern():
    text = "ab" * 100
    pattern = r"(?<=a)(?P<b>b)"
    with io.StringIO(text) as file:
        result = list(parser.parse(file, pattern, chunk=9))
    assert result == [dict(b="b")] * 100

def test_greedy_pattern():
    text = ("\n" + "a" * 100) * 1000
    pattern = r"\n(?P<a>a+)"
    with io.StringIO(text) as file:
        result = list(parser.parse(file, pattern, chunk=30))
    assert result == [dict(a="a" * 100)] * 1000

def test_cast():
    log = dict(num="123", val="1.1", date="2017-03-29 11:11:11")
    result = parser.cast(log, num=int, val=float, date=pendulum.parse)
    assert result == dict(num=123, val=1.1, date=pendulum.parse("2017-03-29 11:11:11"))

def test_cast_with_irrelevant_arg():
    log = dict(a="1")
    result = parser.cast(log, a=int, b=float)
    assert result == dict(a=1)

def test_cast_with_irrelevant_value():
    log = dict(a="1", b=[2, 3, 4])
    result = parser.cast(log, a=int)
    assert result == dict(a=1, b=[2, 3, 4])

@pytest.mark.parametrize('file', [object(), 123, dict])
def test_invalid_file(file):
    with pytest.raises(ValueError):
        next(parser.parse(file, r"pattern"))

@pytest.mark.parametrize('pattern', [object(), 123, dict])
def test_invalid_pattern(fileobj, pattern):
    with pytest.raises(ValueError):
        next(parser.parse(fileobj, pattern))
