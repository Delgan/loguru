import sys

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="{message}", colorize=False, backtrace=True, diagnose=False)


def f():
    try:
        1 / 0
    except ZeroDivisionError:
        ex_type, ex, tb = sys.exc_info()
        tb = None

    logger.opt(exception=(ex_type, ex, tb)).debug("Test:")


f()
