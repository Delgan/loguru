import sys
from loguru import logger

logger.remove()
logger.add(sys.stderr, format="", colorize=True, backtrace=True)


a = b = 0

try:
    a + b"prefix" + 'single' + """triple""" + 1 + b
except TypeError:
    logger.exception("")
