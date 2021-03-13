import sys

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="{message}", diagnose=False, backtrace=False, colorize=False)


def a():
    1 / 0


with logger.catch(message="An error occurred (1):"):
    a()

a = logger.catch(message="An error occurred (2):")(a)
a()
