import sys

import _init
from somelib import syntaxerror

from loguru import logger


def test(*, backtrace, colorize, diagnose):
    logger.remove()
    logger.add(sys.stderr, format="", colorize=colorize, backtrace=backtrace, diagnose=diagnose)

    try:
        syntaxerror()
    except SyntaxError:
        logger.exception("")


test(backtrace=True, colorize=True, diagnose=True)
test(backtrace=False, colorize=True, diagnose=True)
test(backtrace=True, colorize=True, diagnose=False)
test(backtrace=False, colorize=True, diagnose=False)
test(backtrace=False, colorize=False, diagnose=False)
