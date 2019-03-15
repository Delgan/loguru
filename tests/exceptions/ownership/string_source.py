import sys
from loguru import logger

logger.remove()
logger.add(sys.stderr, format="", colorize=True, backtrace=True)

def foo():
    1 / 0

try:
    exec("foo()")
except ZeroDivisionError:
    logger.exception("")
