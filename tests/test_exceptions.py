import pytest
import textwrap
import py
import os
from itertools import zip_longest, dropwhile
import re

@pytest.fixture
def compare_outputs(tmpdir):

    def compare_outputs(to_exec, caught_scope_index, caught_trace_index=0):
        loguru_path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        cfg_loguru = ('import sys;'
                      'sys.path.append("' + loguru_path + '");'
                      'from loguru import logger;'
                      'logger.stop();'
                      'logger.log_to(sys.stdout, better_exceptions=False, colored=False, format="{message}")\n')

        without_loguru = with_loguru = textwrap.dedent(to_exec)
        without_loguru = re.sub('try:', 'if 1:', without_loguru)
        without_loguru = re.sub('except:', '# padding', without_loguru)
        without_loguru = re.sub('.*logger.*', '# padding', without_loguru)

        with_loguru = cfg_loguru + with_loguru
        without_loguru = '# padding\n' + without_loguru

        print("=== Comparing outputs with and without loguru ===")
        print(with_loguru)
        print("==========")
        print(without_loguru)
        print("=================================================")

        file = tmpdir.join('test.py')

        def run():
            return py.process.cmdexec('python %s' % file.realpath())

        try:
            file.write(without_loguru)
            run()
        except py.error.Error as e:
            result_without_loguru = e.err.strip()

        file.write(with_loguru)
        result_with_loguru = run().strip()

        print("--- Compared outputs with and without loguru ---")
        print(result_with_loguru)
        print('----------')
        print(result_without_loguru)
        print("------------------------------------------------")

        result_with_loguru = result_with_loguru.splitlines()
        result_without_loguru = result_without_loguru.splitlines()

        scope_index = trace_index = -1
        for result, expected in zip_longest(result_with_loguru, result_without_loguru):
            if expected.startswith('Traceback'):
                trace_index += 1
                if trace_index == caught_trace_index:
                    assert 'catch point marked' in result
                    result = result.replace(', catch point marked', '', 1)
            if trace_index == caught_trace_index and expected.startswith('  File'):
                scope_index += 1
                if scope_index == caught_scope_index:
                    assert result[0] == '>'
                    result = ' ' + result[1:]
            assert result == expected

    return compare_outputs

def test_simple_explicit(compare_outputs):
    to_exec = """
    try:
        1 / 0
    except:
        logger.exception('')
    """

    compare_outputs(to_exec, 0)

def test_func_explicit(compare_outputs):
    to_exec = """
    def f():
        try:
            1 / 0
        except:
            logger.exception('')
    f()
    """

    compare_outputs(to_exec, 1)

def test_func_decorator(compare_outputs):
    to_exec = """
    @logger.catch(message='')
    def f():
        1 / 0
    f()
    """

    compare_outputs(to_exec, 0)

def test_nested_explicit(compare_outputs):
    to_exec = """
    def a(k):
        def b(i):
            1 / i
        try:
            b(k)
        except:
            logger.exception("")
    a(5)
    a(0)
    """

    compare_outputs(to_exec, 1)

def test_nested_decorator(compare_outputs):
    to_exec = """
    def a(k):
        @logger.catch(message="")
        def b(i):
            1 / i
        b(k)
    a(5)
    a(0)
    """

    compare_outputs(to_exec, 1)

@pytest.mark.parametrize('catch_index', [-1, 0, 1, 2])
def test_chaining_explicit(compare_outputs, catch_index):
    to_exec = """
    def a(): b()
    def b(): c()
    def c(): 1 / 0
    if 1: a()""".strip('\n')

    calls = to_exec.splitlines()

    func, exe = calls[catch_index].split(': ')
    func += ':'

    calls[catch_index] = func + """
        try:
            %s
        except:
            logger.exception('')
    """ % exe
    to_exec = '\n'.join(calls)

    compare_outputs(to_exec, catch_index + 1)

@pytest.mark.parametrize('catch_index', [0, 1, 2, 3])
def test_chaining_decorator(compare_outputs, catch_index):
    to_exec = """
    def main(): a()
    def a(): b()
    def b(): c()
    def c(): 1 / 0
    main()""".strip('\n')

    calls = to_exec.splitlines()
    call = calls[catch_index].strip()

    calls[catch_index] = """
    @logger.catch(message='')
    %s""" % call
    to_exec = '\n'.join(calls)

    compare_outputs(to_exec, catch_index)

@pytest.mark.parametrize('rec', [1, 2, 3])
def test_tail_recursion_explicit(compare_outputs, rec):
    to_exec = """
    def f(n):
        1 / n
        try:
            f(n - 1)
        except:
            logger.exception("")
    f(%d)
    """ % rec

    compare_outputs(to_exec, rec)

@pytest.mark.parametrize('rec', [0, 1, 2, 3])
def test_tail_recursion_decorator(compare_outputs, rec):
    to_exec = """
    @logger.catch(message="")
    def f(n):
        1 / n
        f(n - 1)
    f(%d)
    """ % rec

    compare_outputs(to_exec, rec)

@pytest.mark.parametrize('rec', [1, 2, 3])
def test_head_recursion_explicit(compare_outputs, rec):
    to_exec = """
    def f(n):
        if n:
            try:
                f(n - 1)
            except:
                logger.exception("")
        1 / n
    f(%d)
    """ % rec

    compare_outputs(to_exec, rec)

@pytest.mark.parametrize('rec', [0, 1, 2, 3])
def test_head_recursion_decorator(compare_outputs, rec):
    to_exec = """
    @logger.catch(message="")
    def f(n):
        if n:
            f(n - 1)
        1 / n
    f(%d)
    """ % rec

    compare_outputs(to_exec, rec)

def test_chained_exception_explicit(compare_outputs):
    to_exec = """
    def a():
        try :
            1 / 0
        except :
            raise ValueError("NOK")
    def b():
        try:
            a()
        except:
            logger.exception('')
    b()
    """

    compare_outputs(to_exec, 1, 1)

def test_chained_exception_decorator(compare_outputs):
    to_exec = """
    def a():
        try :
            1 / 0
        except :
            raise ValueError("NOK")
    @logger.catch(message='')
    def b():
        a()
    b()
    """

    compare_outputs(to_exec, 0, 1)

def test_suppressed_exception_explicit(compare_outputs):
    to_exec = """
    def a(x, y):
        x / y
    def b():
        try :
            a(1, 0)
        except ZeroDivisionError as e:
            raise ValueError("NOK") from e
    def c():
        try:
            b()
        except:
            logger.exception('')
    c()
    """

    compare_outputs(to_exec, 1, 1)

def test_suppressed_exception_decorator(compare_outputs):
    to_exec = """
    def a(x, y):
        x / y
    def b():
        try :
            a(1, 0)
        except ZeroDivisionError as e:
            raise ValueError("NOK") from e
    @logger.catch(message='')
    def c():
        b()
    c()
    """

    compare_outputs(to_exec, 0, 1)

@pytest.mark.parametrize('rec', [1, 2, 3])
def test_raising_recursion_explicit(logger, writer, rec):
    logger.log_to(writer, format='{message}', better_exceptions=False)

    def f(n):
        if n:
            try:
                f(n - 1)
            except:
                logger.exception("")
        n / 0
    try :
        f(rec)
    except :
        pass

    lines = writer.read().splitlines()

    assert sum(line.startswith("Traceback") for line in lines) == rec

@pytest.mark.parametrize('rec', [0, 1, 2, 3])
def test_raising_recursion_decorator(logger, writer, rec):
    logger.log_to(writer, format='{message}', better_exceptions=False)

    @logger.catch(message="")
    def f(n):
        if n:
            f(n - 1)
        n / 0
    f(rec)

    lines = writer.read().splitlines()

    assert sum(line.startswith("Traceback") for line in lines) == rec + 1

def test_carret_not_masked(logger, writer):
    logger.log_to(writer, better_exceptions=False, colored=False)

    @logger.catch
    def f(n):
        1 / n
        f(n - 1)

    f(20)

    lines = writer.read().splitlines()

    assert sum(line.startswith('> File') for line in lines) == 1

def test_frame_values_backward(logger, writer):
    logger.log_to(writer, better_exceptions=True, colored=False)

    k = 2

    @logger.catch
    def a(n):
        1 / n
    def b(n):
        a(n - 1)
    def c(n):
        b(n - 1)

    c(k)

    lines = [line.strip() for line in writer.read().splitlines()]

    line_1 = dropwhile(lambda x: x != '1 / n', lines)
    line_2 = dropwhile(lambda x: x != 'a(n - 1)', lines)
    line_3 = dropwhile(lambda x: x != 'b(n - 1)', lines)
    line_4 = dropwhile(lambda x: x != 'c(k)', lines)

    next(line_1); next(line_2); next(line_3); next(line_4)

    assert next(line_1).endswith(' 0')
    assert next(line_2).endswith(' 1')
    assert next(line_3).endswith(' 2')
    assert next(line_4).endswith(' 2')


def test_frame_values_forward(logger, writer):
    logger.log_to(writer, better_exceptions=True, colored=False)

    k = 2

    def a(n):
        1 / n
    def b(n):
        a(n - 1)
    @logger.catch
    def c(n):
        b(n - 1)

    c(k)

    lines = [line.strip() for line in writer.read().splitlines()]

    line_1 = dropwhile(lambda x: x != '1 / n', lines)
    line_2 = dropwhile(lambda x: x != 'a(n - 1)', lines)
    line_3 = dropwhile(lambda x: x != 'b(n - 1)', lines)
    line_4 = dropwhile(lambda x: x != 'c(k)', lines)

    next(line_1); next(line_2); next(line_3); next(line_4)

    assert next(line_1).endswith(' 0')
    assert next(line_2).endswith(' 1')
    assert next(line_3).endswith(' 2')
    assert next(line_4).endswith(' 2')
