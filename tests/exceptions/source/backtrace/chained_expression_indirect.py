import sys

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="", colorize=False, backtrace=True, diagnose=False)


def a():
    try:
        1 / 0
    except ZeroDivisionError:
        raise ValueError("NOK")


@logger.catch
def b():
    a()


b()

with logger.catch():
    a()

try:
    a()
except ValueError:
    logger.exception("")
