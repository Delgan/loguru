import sys

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="", colorize=False, backtrace=True, diagnose=False)


@logger.catch
def a_decorated():
    b()


def a_not_decorated():
    b()


def b():
    c()


def c():
    1 / 0


a_decorated()


with logger.catch():
    a_not_decorated()

try:
    a_not_decorated()
except ZeroDivisionError:
    logger.exception("")
