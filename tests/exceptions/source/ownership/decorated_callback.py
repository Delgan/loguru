import os, site, sys
from usersite.lib import callme, divide
from loguru import logger

site.USER_SITE = os.path.abspath(os.path.join(os.path.dirname(__file__), "usersite"))


def test(*, backtrace, colorize, diagnose):
    logger.remove()
    logger.add(sys.stderr, format="", colorize=colorize, backtrace=backtrace, diagnose=diagnose)

    @logger.catch
    def callback():
        a, b = 1, 0
        a / b

    callme(callback)


test(backtrace=True, colorize=True, diagnose=True)
test(backtrace=False, colorize=True, diagnose=True)
test(backtrace=True, colorize=True, diagnose=False)
test(backtrace=False, colorize=True, diagnose=False)
test(backtrace=False, colorize=False, diagnose=False)
