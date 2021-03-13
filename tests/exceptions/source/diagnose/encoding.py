import sys

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="", colorize=True, backtrace=False, diagnose=True)


def _deep(val):
    return 1 / val


def div():
    return _deep("天")


try:
    div()
except TypeError:
    logger.exception("")
