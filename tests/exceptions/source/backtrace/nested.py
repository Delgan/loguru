import sys

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="", colorize=False, backtrace=True, diagnose=False)


def a(x):
    @logger.catch
    def nested(i):
        1 / i

    nested(x)


a(0)


def b(x):
    def nested(i):
        1 / i

    with logger.catch():
        nested(x)


b(0)


def c(x):
    def nested(i):
        1 / i

    try:
        nested(x)
    except ZeroDivisionError:
        logger.exception("")


c(0)
