import sys
from loguru import logger

logger.remove()
logger.add(sys.stderr, format="", colorize=True, backtrace=True)


def foo():
    raise ValueError("")


def bar():
    foo()


try:
    bar()
except ValueError:
    logger.exception("")
