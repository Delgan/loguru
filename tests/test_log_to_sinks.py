# coding: utf-8

import pathlib
import sys

import loguru

import pytest

MESSAGES = ['ASCII test']
PARAMS = [(message, message + '\n') for message in MESSAGES]

messages = pytest.mark.parametrize('message, expected', PARAMS)
repetitions = pytest.mark.parametrize('rep', [0, 1, 2])


def log(sink, message, rep=1):
    logger = loguru.Logger()
    logger.debug("This shouldn't be printed.")
    logger.log_to(sink, format='{message}')
    for i in range(rep):
        logger.debug(message)

@messages
@repetitions
def test_stdout_sink(message, expected, rep, capsys):
    log(sys.stdout, message, rep)
    out, err = capsys.readouterr()
    assert out == expected * rep
    assert err == ''

@messages
@repetitions
def test_stderr_sink(message, expected, rep, capsys):
    log(sys.stderr, message, rep)
    out, err = capsys.readouterr()
    assert out == ''
    assert err == expected * rep

@messages
@repetitions
@pytest.mark.parametrize("sink_from_path", [
    str,
    pathlib.Path,
    lambda path: open(path, 'a'),
    lambda path: pathlib.Path(path).open('a'),
])
def test_file_sink(message, expected, rep, sink_from_path, tmpdir):
    file = tmpdir.join('test.log')
    path = file.realpath()
    sink = sink_from_path(path)
    log(sink, message, rep)
    assert file.read() == expected * rep

@messages
@repetitions
def test_function_sink(message, expected, rep):
    a = []
    func = lambda log_message: a.append(log_message)
    log(func, message, rep)
    assert a == [expected] * rep

@messages
@repetitions
def test_class_sink(message, expected, rep):
    out = []
    class A:
        def write(self, m): out.append(m)
    log(A, message, rep)
    assert out == [expected] * rep

@messages
@repetitions
def test_file_object_sink(message, expected, rep):
    class A:
        def __init__(self): self.out = ""
        def write(self, m): self.out += m
    a = A()
    log(a, message, rep)
    assert a.out == expected * rep

@pytest.mark.parametrize('sink', [123, sys, object(), loguru.Logger(), loguru.Logger])
def test_invalid_sink(sink):
    with pytest.raises(ValueError):
        log(sink, "")
