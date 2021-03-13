import sys

from loguru import logger

logger.remove()
logger.add(sys.stderr, enqueue=True, format="", colorize=False, backtrace=True, diagnose=False)

try:
    1 / 0
except ZeroDivisionError:
    logger.exception("Error")
