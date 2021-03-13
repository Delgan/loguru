import sys

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="", colorize=True, backtrace=False, diagnose=True)


class Object:
    def __repr__(self):
        raise RuntimeError("No way!")


try:
    obj = Object()
    obj + 1 / 0
except ZeroDivisionError:
    logger.exception("")
