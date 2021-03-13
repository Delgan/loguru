import sys

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="", colorize=False, backtrace=True, diagnose=False)


@logger.catch
def decorated():
    pass


def not_decorated():
    pass


decorated(1)

with logger.catch():
    not_decorated(2)

try:
    not_decorated(3)
except TypeError:
    logger.exception("")
