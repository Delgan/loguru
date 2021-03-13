import sys

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="", diagnose=False, backtrace=False, colorize=False)
logger.add(sys.stderr, format="", diagnose=True, backtrace=False, colorize=False)
logger.add(sys.stderr, format="", diagnose=False, backtrace=True, colorize=False)
logger.add(sys.stderr, format="", diagnose=True, backtrace=True, colorize=False)


@logger.catch
def a(a, b):
    a / b


a(1, 0)
