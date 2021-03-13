import sys

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="", colorize=False, backtrace=True, diagnose=False)


def f(i):
    1 / i


@logger.catch
@logger.catch()
def a(x):
    f(x)


a(0)


with logger.catch():
    with logger.catch():
        f(0)


try:
    try:
        f(0)
    except ZeroDivisionError:
        logger.exception("")
except Exception:
    logger.exception("")
