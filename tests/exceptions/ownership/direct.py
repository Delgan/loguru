import os, site, sys
from usersite.lib import divide
from loguru import logger

site.USER_SITE = os.path.abspath(os.path.join(os.path.dirname(__file__), "usersite"))


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
