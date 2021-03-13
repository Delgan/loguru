import sys

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="", colorize=False, backtrace=True, diagnose=False)


@logger.catch()
def a():
    1 / 0


def b():
    2 / 0


def c():
    3 / 0


a()

with logger.catch():
    b()

try:
    c()
except ZeroDivisionError:
    logger.exception("")
