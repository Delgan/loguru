import sys

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="", colorize=False, backtrace=True, diagnose=False)


@logger.catch()
def a(n):
    1 / n
    a(n - 1)


def b(n):
    1 / n
    with logger.catch():
        b(n - 1)


def c(n):
    1 / n
    try:
        c(n - 1)
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
