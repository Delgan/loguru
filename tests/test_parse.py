import io
import pathlib
import re
from datetime import datetime

import pytest

from loguru import logger

TEXT = "This\nIs\nRandom\nText\n123456789\nABC!DEF\nThis Is The End\n"


@pytest.fixture
def fileobj():
    with io.StringIO(TEXT) as file:
        yield file


def test_parse_file(tmpdir):
    file = tmpdir.join("test.log")
    file.write(TEXT)
    result, *_ = list(logger.parse(str(file), r"(?P<num>\d+)"))
    assert result == dict(num="123456789")


def test_parse_fileobj(tmpdir):
    file = tmpdir.join("test.log")
    file.write(TEXT)
    result, *_ = list(logger.parse(open(str(file)), r"^(?P<t>\w+)"))
    assert result == dict(t="This")


def test_parse_pathlib(tmpdir):
    file = tmpdir.join("test.log")
    file.write(TEXT)
    result, *_ = list(logger.parse(pathlib.Path(str(file)), r"(?P<r>Random)"))
    assert result == dict(r="Random")


def test_parse_string_pattern(fileobj):
    result, *_ = list(logger.parse(fileobj, r"(?P<num>\d+)"))
    assert result == dict(num="123456789")


def test_parse_regex_pattern(fileobj):
    regex = re.compile(r"(?P<maj>[a-z]*![a-z]*)", flags=re.I)
    result, *_ = list(logger.parse(fileobj, regex))
    assert result == dict(maj="ABC!DEF")


def test_parse_multiline_pattern(fileobj):
    result, *_ = list(logger.parse(fileobj, r"(?P<text>This[\s\S]*Text\n)"))
    assert result == dict(text="This\nIs\nRandom\nText\n")


def test_parse_without_group(fileobj):
    result, *_ = list(logger.parse(fileobj, r"\d+"))
    assert result == {}


def test_parse_bytes():
    with io.BytesIO(b"Testing bytes!") as fileobj:
        result, *_ = list(logger.parse(fileobj, br"(?P<ponct>[?!:])"))
    assert result == dict(ponct=b"!")


@pytest.mark.parametrize("chunk", [-1, 1, 2 ** 16])
def test_chunk(fileobj, chunk):
    result, *_ = list(logger.parse(fileobj, r"(?P<a>[ABC]+)", chunk=chunk))
    assert result == dict(a="ABC")


def test_positive_lookbehind_pattern():
    text = "ab" * 100
    pattern = r"(?<=a)(?P<b>b)"
    with io.StringIO(text) as file:
        result = list(logger.parse(file, pattern, chunk=9))
    assert result == [dict(b="b")] * 100


def test_greedy_pattern():
    text = ("\n" + "a" * 100) * 1000
    pattern = r"\n(?P<a>a+)"
    with io.StringIO(text) as file:
        result = list(logger.parse(file, pattern, chunk=30))
    assert result == [dict(a="a" * 100)] * 1000


def test_cast_dict(tmpdir):
    file = tmpdir.join("test.log")
    file.write("[123] [1.1] [2017-03-29 11:11:11]\n")
    regex = r"\[(?P<num>.*)\] \[(?P<val>.*)\] \[(?P<date>.*)\]"
    caster = dict(num=int, val=float, date=lambda d: datetime.strptime(d, "%Y-%m-%d %H:%M:%S"))
    result = next(logger.parse(str(file), regex, cast=caster))
    assert result == dict(num=123, val=1.1, date=datetime(2017, 3, 29, 11, 11, 11))


def test_cast_function(tmpdir):
    file = tmpdir.join("test.log")
    file.write("[123] [1.1] [2017-03-29 11:11:11]\n")
    regex = r"\[(?P<num>.*)\] \[(?P<val>.*)\] \[(?P<date>.*)\]"

    def caster(groups):
        groups["num"] = int(groups["num"])
        groups["val"] = float(groups["val"])
        groups["date"] = datetime.strptime(groups["date"], "%Y-%m-%d %H:%M:%S")

    result = next(logger.parse(str(file), regex, cast=caster))
    assert result == dict(num=123, val=1.1, date=datetime(2017, 3, 29, 11, 11, 11))


def test_cast_with_irrelevant_arg(tmpdir):
    file = tmpdir.join("test.log")
    file.write("[123] Blabla")
    regex = r"\[(?P<a>\d+)\] .*"
    caster = dict(a=int, b=float)
    result = next(logger.parse(str(file), regex, cast=caster))
    assert result == dict(a=123)


def test_cast_with_irrelevant_value(tmpdir):
    file = tmpdir.join("test.log")
    file.write("[123] Blabla")
    regex = r"\[(?P<a>\d+)\] (?P<b>.*)"
    caster = dict(a=int)
    result = next(logger.parse(str(file), regex, cast=caster))
    assert result == dict(a=123, b="Blabla")


@pytest.mark.parametrize("file", [object(), 123, dict])
def test_invalid_file(file):
    with pytest.raises(TypeError):
        next(logger.parse(file, r"pattern"))


@pytest.mark.parametrize("pattern", [object(), 123, dict])
def test_invalid_pattern(fileobj, pattern):
    with pytest.raises(TypeError):
        next(logger.parse(fileobj, pattern))


@pytest.mark.parametrize("cast", [object(), 123])
def test_invalid_cast(fileobj, cast):
    with pytest.raises(TypeError):
        next(logger.parse(fileobj, r"pattern", cast=cast))
