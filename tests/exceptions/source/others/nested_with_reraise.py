import sys

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="", diagnose=False, backtrace=False, colorize=False)
logger.add(sys.stderr, format="", diagnose=True, backtrace=False, colorize=False)
logger.add(sys.stderr, format="", diagnose=False, backtrace=True, colorize=False)
logger.add(sys.stderr, format="", diagnose=True, backtrace=True, colorize=False)


@logger.catch(reraise=True)
def foo(a, b):
    a / b


@logger.catch
def bar(x, y):
    try:
        f = foo(x, y)
    except Exception as e:
        raise ValueError from e


def baz():
    bar(1, 0)


if __name__ == "__main__":
    baz()
