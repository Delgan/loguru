import sys
from loguru import logger

logger.remove()
logger.add(sys.stderr, format="", colorize=True, backtrace=True)


def f():
    1 / 0


with logger.catch():
    f()
