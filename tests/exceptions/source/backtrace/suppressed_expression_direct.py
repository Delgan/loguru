import sys

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="", colorize=False, backtrace=True, diagnose=False)


def a(x, y):
    x / y


@logger.catch
def b_decorated():
    try:
        a(1, 0)
    except ZeroDivisionError as e:
        raise ValueError("NOK") from e


def b_not_decorated():
    try:
        a(1, 0)
    except ZeroDivisionError as e:
        raise ValueError("NOK") from e


def c_decorator():
    b_decorated()


def c_context_manager():
    with logger.catch():
        b_not_decorated()


def c_explicit():
    try:
        b_not_decorated()
    except ValueError:
        logger.exception("")


c_decorator()
c_context_manager()
c_explicit()
