import sys

import _init
from somelib import divide

from loguru import logger


def test(*, backtrace, colorize, diagnose):
    logger.remove()
    logger.add(sys.stderr, format="", colorize=colorize, backtrace=backtrace, diagnose=diagnose)

    try:
        divide(10, 0)
    except ZeroDivisionError:
        logger.exception("")


test(backtrace=True, colorize=True, diagnose=True)
test(backtrace=False, colorize=True, diagnose=True)
test(backtrace=True, colorize=True, diagnose=False)
test(backtrace=False, colorize=True, diagnose=False)
test(backtrace=False, colorize=False, diagnose=False)
