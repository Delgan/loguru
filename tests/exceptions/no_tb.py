import sys
from loguru import logger


def f():
    try:
        1 / 0
    except ZeroDivisionError:
        ex_type, ex, tb = sys.exc_info()
        tb = None

    logger.opt(exception=(ex_type, ex, tb)).debug("Test")


logger.remove()
logger.add(sys.stderr, format="", colorize=False, backtrace=False)
f()


logger.remove()
logger.add(sys.stderr, format="", colorize=False, backtrace=True)
f()
