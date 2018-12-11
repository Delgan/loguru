import pytest
import traceback
import textwrap
import re
from loguru import logger

zero_division_error = "ZeroDivisionError: division by zero\n"
wrap_mode = pytest.mark.parametrize("wrap_mode", ["decorator", "function", "context_manager"])


@pytest.mark.parametrize("use_parentheses", [True, False])
def test_decorator(writer, use_parentheses):
    logger.add(writer)

    if use_parentheses:

        @logger.catch()
        def c(a, b):
            a / b

        c(5, b=0)
    else:

        @logger.catch
        def c(a, b=0):
            a / b

        c(2)

    assert writer.read().endswith(zero_division_error)


def test_context_manager(writer):
    logger.add(writer)

    with logger.catch():
        1 / 0

    assert writer.read().endswith(zero_division_error)


def test_function(writer):
    logger.add(writer)

    def a():
        1 / 0

    a = logger.catch()(a)
    a()

    assert writer.read().endswith(zero_division_error)


def test_with_backtrace(writer):
    logger.add(writer, backtrace=True)

    def c():
        a = 2
        b = 0
        a / b

    decorated = logger.catch()(c)
    decorated()

    result_with = writer.read()

    logger.remove()
    writer.clear()

    logger.add(writer, backtrace=False)

    decorated = logger.catch()(c)
    decorated()

    result_without = writer.read()

    assert len(result_with) > len(result_without)
    assert result_with.endswith(zero_division_error)
    assert result_without.endswith(zero_division_error)


@pytest.mark.parametrize(
    "exception, should_raise",
    [
        (ZeroDivisionError, False),
        (ValueError, True),
        ((ZeroDivisionError, ValueError), False),
        ((SyntaxError, TypeError), True),
    ],
)
@pytest.mark.parametrize("keyword", [True, False])
@wrap_mode
def test_exception(writer, exception, should_raise, keyword, wrap_mode):
    logger.add(writer)

    if keyword:
        if wrap_mode == "decorator":

            @logger.catch(exception=exception)
            def a():
                1 / 0

        elif wrap_mode == "function":

            def a():
                1 / 0

            a = logger.catch(exception=exception)(a)
        elif wrap_mode == "context_manager":

            def a():
                with logger.catch(exception=exception):
                    1 / 0

    else:
        if wrap_mode == "decorator":

            @logger.catch(exception)
            def a():
                1 / 0

        elif wrap_mode == "function":

            def a():
                1 / 0

            a = logger.catch(exception)(a)
        elif wrap_mode == "context_manager":

            def a():
                with logger.catch(exception):
                    1 / 0

    if should_raise:
        with pytest.raises(ZeroDivisionError):
            a()
        assert writer.read() == ""
    else:
        a()
        assert writer.read().endswith(zero_division_error)


@wrap_mode
def test_message(writer, wrap_mode):
    logger.add(writer, format="{message}")
    message = "An error occured:"

    if wrap_mode == "decorator":

        @logger.catch(message=message)
        def a():
            1 / 0

        a()
    elif wrap_mode == "function":

        def a():
            1 / 0

        a = logger.catch(message=message)(a)
        a()
    elif wrap_mode == "context_manager":
        with logger.catch(message=message):
            1 / 0

    assert writer.read().startswith(message + "\n")


@wrap_mode
@pytest.mark.parametrize("level, expected", [(13, "Level 13 | 13"), ("DEBUG", "DEBUG | 10")])
def test_level(writer, wrap_mode, level, expected):
    logger.add(writer, format="{level.name} | {level.no}")

    if wrap_mode == "decorator":

        @logger.catch(level=level)
        def a():
            1 / 0

    elif wrap_mode == "function":

        def a():
            1 / 0

        a = logger.catch(level=level)(a)
    elif wrap_mode == "context_manager":

        def a():
            with logger.catch(level=level):
                1 / 0

    a()

    lines = writer.read().strip().splitlines()
    assert lines[0] == expected


@wrap_mode
def test_reraise(writer, wrap_mode):
    logger.add(writer)

    if wrap_mode == "decorator":

        @logger.catch(reraise=True)
        def a():
            1 / 0

    elif wrap_mode == "function":

        def a():
            1 / 0

        a = logger.catch(reraise=True)(a)
    elif wrap_mode == "context_manager":

        def a():
            with logger.catch(reraise=True):
                1 / 0

    with pytest.raises(ZeroDivisionError):
        a()

    assert writer.read().endswith(zero_division_error)


@wrap_mode
def test_not_raising(writer, wrap_mode):
    logger.add(writer, format="{message}")
    message = "It's ok"

    if wrap_mode == "decorator":

        @logger.catch
        def a():
            logger.debug(message)

        a()
    elif wrap_mode == "function":

        def a():
            logger.debug(message)

        a = logger.catch()(a)
        a()
    elif wrap_mode == "context_manager":
        with logger.catch():
            logger.debug(message)

    assert writer.read() == message + "\n"


@pytest.mark.parametrize(
    "format, expected_dec, expected_ctx",
    [
        ("{name}", "folder.test", "folder.test"),
        ("{file}", "test.py", "test.py"),
        ("{function}", "<module>", "myfunc"),
        ("{module}", "test", "test"),
        ("{line}", "10", "8"),
    ],
)
@wrap_mode
def test_formatting(tmpdir, pyexec, wrap_mode, format, expected_dec, expected_ctx):
    logfile = tmpdir.join("test.log")
    pyfile = tmpdir.join("folder", "test.py")
    pyfile.write("", ensure=True)

    message = "{record[%s]}" % format[1:-1]
    format += " --- {message}"

    if wrap_mode == "decorator":
        catch = "@logger.catch(message='%s')" % message
        ctx = "if 1"
        post = "# padding"
    elif wrap_mode == "function":
        catch = "# padding"
        ctx = "if 1"
        post = "myfunc = logger.catch( message='%s')(myfunc)" % message
    elif wrap_mode == "context_manager":
        catch = "# padding"
        ctx = "with logger.catch(message='%s')" % message
        post = "# padding"

    code = """
    from loguru import logger
    logger.add(r"{logfile}", format="{fmt}")
    def k():
        1 / 0
    {catch}
    def myfunc():
        {ctx}:
            k()
    {post}
    myfunc()
    """
    code = code.format(logfile=str(logfile.realpath()), fmt=format, catch=catch, ctx=ctx, post=post)
    code = textwrap.dedent(code).strip()

    pyfile.write(code)

    pyexec("import folder.test", True, pyfile=tmpdir.join("main.py"))

    lines = logfile.read().strip().splitlines()
    expected = expected_dec if wrap_mode in ["decorator", "function"] else expected_ctx

    start, end = lines[0].split(" --- ")
    assert start == expected
    assert end == expected
    assert lines[-1] == zero_division_error.strip()


@wrap_mode
def test_returnwriter(writer, wrap_mode):
    logger.add(writer, format="{message}")

    if wrap_mode == "decorator":

        @logger.catch
        def a(x):
            return 100 / x

        result = a(50)
    elif wrap_mode == "function":

        def a(x):
            return 100 / x

        a = logger.catch()(a)
        result = a(50)
    elif wrap_mode == "context_manager":

        def a(x):
            with logger.catch():
                return 100 / x

        result = a(50)

    assert writer.read() == ""
    assert result == 2
