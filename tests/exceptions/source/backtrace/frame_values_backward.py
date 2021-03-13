import sys

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="", colorize=False, backtrace=True, diagnose=False)

k = 2


@logger.catch
def a(n):
    1 / n


def b(n):
    a(n - 1)


def c(n):
    b(n - 1)


c(k)
