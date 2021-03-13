import sys

from loguru import logger

# fmt: off

logger.remove()
logger.add(sys.stderr, format="", colorize=True, backtrace=False, diagnose=True)


a = b = 0

try:
    a + b"prefix" + 'single' + """triple""" + 1 + b
except TypeError:
    logger.exception("")
