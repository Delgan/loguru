import sys

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="", colorize=False, backtrace=True, diagnose=False)


@logger.catch
def a(n):
    if n:
        a(n - 1)
    n / 0


def b(n):
    with logger.catch():
        if n:
            b(n - 1)
        n / 0


def c(n):
    try:
        if n:
            c(n - 1)
        n / 0
    except ZeroDivisionError:
        logger.exception("")


a(1)
a(2)
a(3)

b(1)
b(2)
b(3)

c(1)
c(2)
c(3)
