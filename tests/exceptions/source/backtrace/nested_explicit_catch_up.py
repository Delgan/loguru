import sys

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="", colorize=False, backtrace=False, diagnose=False)
logger.add(sys.stderr, format="", colorize=False, backtrace=True, diagnose=False)


def foo():
    bar()


@logger.catch(NotImplementedError)
def bar():
    1 / 0


try:
    foo()
except ZeroDivisionError:
    logger.exception("")
