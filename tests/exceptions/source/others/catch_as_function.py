import sys

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="", diagnose=False, backtrace=False, colorize=False)


def a():
    1 / 0


a = logger.catch()(a)
a()
