import pytest
import textwrap
import py
import os
from itertools import zip_longest, dropwhile
import re

@pytest.fixture
def compare_outputs(tmpdir):

    def compare_outputs(with_loguru, without_loguru, caught_scope_index, caught_trace_index=0):
        print("=== Comparing outputs with and without loguru ===")
        print(with_loguru)
        print("==========")
        print(without_loguru)
        print("=================================================")

        file = tmpdir.join('test.py')

        def run():
            return py.process.cmdexec('python %s' % file.realpath())

        file.write(with_loguru)
        result_with_loguru = run().strip()

        try:
            file.write(without_loguru)
            run()
        except py.error.Error as e:
            result_without_loguru = e.err.strip()

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

@pytest.fixture(params=['explicit', 'decorator', 'context_manager'])
def compare(compare_outputs, request):
    catch_mode = request.param

    loguru_path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    cfg_loguru = ('import sys;'
                  'sys.path.append("' + loguru_path + '");'
                  'from loguru import logger;'
                  'logger.clear();'
                  'logger.log_to(sys.stdout, better_exceptions=False, colored=False, format="{message}")\n')

    def compare(template, caught_scope_index, caught_trace_index=0, *, disabled=[]):
        template = textwrap.dedent(template)

        without_dict = {
            "try": "if 1",
            "except": "if 1",
            "catch": "# padding",
            "log": "pass",
        }

        if catch_mode == 'explicit':
            with_dict = {
                "try": "try",
                "except": "except",
                "catch": "# padding",
                "log": "logger.exception('')",
            }
        elif catch_mode == 'decorator':
            with_dict = {
                "try": "if 1",
                "except": "if 1",
                "catch": "@logger.catch(message='')",
                "log": "pass",
            }
        elif catch_mode == 'context_manager':
            with_dict = {
                "try": "with logger.catch(message='')",
                "except": "if 1",
                "catch": "# padding",
                "log": "pass",
            }

        without_loguru = template.format_map(without_dict)
        with_loguru = template.format_map(with_dict)

        with_loguru = cfg_loguru + with_loguru
        without_loguru = '# padding\n' + without_loguru

        compare_outputs(with_loguru, without_loguru, caught_scope_index, caught_trace_index)

    return compare


def test_func(compare):
    template = """
    {catch}
    def f():
        1 / 0

    {try}:
        f()
    {except}:
        {log}
    """

    compare(template, 0)

def test_nested(compare):
    template = """
    def a(k):

        {catch}
        def b(i):
            1 / i

        {try}:
            b(k)
        {except}:
            {log}

    a(5)
    a(0)
    """

    compare(template, 1)

def test_chaining_first(compare):
    template = """
    {catch}
    def a(): b()

    def b(): c()

    def c(): 1 / 0

    {try}:
        a()
    {except}:
        {log}
    """

    compare(template, 0)

def test_chaining_second(compare):
    template = """
    def a():
        {try}:
            b()
        {except}:
            {log}

    {catch}
    def b(): c()

    def c(): 1 / 0

    a()
    """

    compare(template, 1)

def test_chaining_third(compare):
    template = """
    def a(): b()

    def b():
        {try}:
            c()
        {except}:
            {log}

    {catch}
    def c(): 1 / 0

    a()
    """

    compare(template, 2)

@pytest.mark.parametrize('rec', [1, 2, 3])
def test_tail_recursion(compare, rec):
    template = """
    {catch}
    def f(n):
        1 / n
        {try}:
            f(n - 1)
        {except}:
            {log}
    f(%d)
    """ % rec

    compare(template, rec)

@pytest.mark.parametrize('rec', [1, 2, 3])
def test_head_recursion(compare, rec):
    template = """
    {catch}
    def f(n):
        if n:
            {try}:
                f(n - 1)
            {except}:
                {log}
        1 / n
    f(%d)
    """ % rec

    compare(template, rec)

def test_chained_exception_direct(compare):
    template = """
    {catch}
    def a():
        try:
            1 / 0
        except:
            raise ValueError("NOK")

    def b():
        {try}:
            a()
        {except}:
            {log}

    b()
    """

    compare(template, 1, 1)

def test_chained_exception_indirect(compare):
    template = """
    def a():
        try:
            1 / 0
        except:
            raise ValueError("NOK")

    {catch}
    def b():
        a()

    {try}:
        b()
    {except}:
        {log}
    """

    compare(template, 0, 1)

def test_suppressed_exception_direct(compare):
    template = """
    def a(x, y):
        x / y

    {catch}
    def b():
        try :
            a(1, 0)
        except ZeroDivisionError as e:
            raise ValueError("NOK") from e

    def c():
        {try}:
            b()
        {except}:
            {log}

    c()
    """

    compare(template, 1, 1)

def test_suppressed_exception_indirect(compare):
    template = """
    def a(x, y):
        x / y

    def b():
        try :
            a(1, 0)
        except ZeroDivisionError as e:
            raise ValueError("NOK") from e

    {catch}
    def c():
        b()

    {try}:
        c()
    {except}:
        {log}
    """

    compare(template, 0, 1)

@pytest.mark.parametrize('rec', [1, 2, 3])
@pytest.mark.parametrize('catch_mode', ['explicit', 'decorator', 'context_manager'])
def test_raising_recursion(logger, writer, rec, catch_mode):
    logger.log_to(writer, format='{message}', better_exceptions=False)

    if catch_mode == 'explicit':
        def f(n):
            try:
                if n:
                    f(n - 1)
                n / 0
            except:
                logger.exception("")
    elif catch_mode == 'decorator':
        @logger.catch(message='')
        def f(n):
            if n:
                f(n - 1)
            n / 0
    elif catch_mode == 'context_manager':
        def f(n):
            with logger.catch(message=''):
                if n:
                    f(n - 1)
                n / 0

    f(rec)

    lines = writer.read().splitlines()

    assert sum(line.startswith("Traceback") for line in lines) == rec + 1
    assert sum(line.startswith("> File") for line in lines) == rec + 1
    for line in lines:
        if line.startswith("> File"):
            assert line.endswith("in f")

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
