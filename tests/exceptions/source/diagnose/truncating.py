import sys

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="", colorize=True, backtrace=False, diagnose=True)


def div():
    var = "9" * 150
    return 1 / var


try:
    div()
except TypeError:
    logger.exception("")
