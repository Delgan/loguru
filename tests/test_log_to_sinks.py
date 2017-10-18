# coding: utf-8

import pathlib
import sys

import loguru

import pytest


message = "test message"
expected = message + "\n"

repetitions = pytest.mark.parametrize('rep', [0, 1, 2])

def log(sink, rep=1):
    logger = loguru.Logger()
    logger.debug("This shouldn't be printed.")
    i = logger.log_to(sink, format='{message}')
    for _ in range(rep):
        logger.debug(message)
    logger.stop(i)
    logger.debug("This shouldn't be printed neither.")

@repetitions
def test_stdout_sink(rep, capsys):
    log(sys.stdout, rep)
    out, err = capsys.readouterr()
    assert out == expected * rep
    assert err == ''

@repetitions
def test_stderr_sink(rep, capsys):
    log(sys.stderr, rep)
    out, err = capsys.readouterr()
    assert out == ''
    assert err == expected * rep

@repetitions
@pytest.mark.parametrize("sink_from_path", [
    str,
    pathlib.Path,
    lambda path: open(path, 'a'),
    lambda path: pathlib.Path(path).open('a'),
])
def test_file_sink(rep, sink_from_path, tmpdir):
    file = tmpdir.join('test.log')
    path = file.realpath()
    sink = sink_from_path(path)
    log(sink, rep)
    assert file.read() == expected * rep

@repetitions
def test_function_sink(rep):
    a = []
    func = lambda log_message: a.append(log_message)
    log(func, rep)
    assert a == [expected] * rep

@repetitions
def test_class_sink(rep):
    out = []
    class A:
        def write(self, m): out.append(m)
    log(A, rep)
    assert out == [expected] * rep

@repetitions
def test_file_object_sink(rep):
    class A:
        def __init__(self): self.out = ""
        def write(self, m): self.out += m
    a = A()
    log(a, rep)
    assert a.out == expected * rep

@pytest.mark.parametrize('sink', [123, sys, object(), loguru.Logger(), loguru.Logger])
def test_invalid_sink(sink):
    with pytest.raises(ValueError):
        log(sink, "")

def test_stop_all(tmpdir, writer, capsys):
    logger = loguru.Logger()
    file = tmpdir.join("test.log")

    logger.debug("This shouldn't be printed.")

    logger.log_to(file.realpath(), format='{message}')
    logger.log_to(sys.stdout, format='{message}')
    logger.log_to(sys.stderr, format='{message}')
    logger.log_to(writer, format='{message}')

    logger.debug(message)

    logger.stop()

    logger.debug("This shouldn't be printed neither.")

    out, err = capsys.readouterr()

    assert file.read() == expected
    assert out == expected
    assert err == expected
    assert writer.read() == expected

def test_stop_count(logger, writer):
    n = logger.stop()
    assert n == 0

    n = logger.stop(42)
    assert n == 0

    i = logger.log_to(writer)
    n = logger.stop(i)
    assert n == 1

    logger.log_to(writer)
    logger.log_to(writer)
    n = logger.stop()
    assert n == 2

    n = logger.stop(0)
    assert n == 0
