import sys

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="", colorize=False, backtrace=True, diagnose=False)


def a(x, y):
    x / y


def b():
    try:
        a(1, 0)
    except ZeroDivisionError as e:
        raise ValueError("NOK") from e


@logger.catch
def c_decorated():
    b()


def c_not_decorated():
    b()


c_decorated()

with logger.catch():
    c_not_decorated()

try:
    c_not_decorated()
except ValueError:
    logger.exception("")
