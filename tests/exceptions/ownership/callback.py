import os, site, sys
from usersite.lib import callme, divide
from loguru import logger

site.USER_SITE = os.path.abspath(os.path.join(os.path.dirname(__file__), "usersite"))
logger.remove()
logger.add(sys.stderr, format="", colorize=True, backtrace=True, diagnose=True)

def callback():
    divide(1, 0)

try:
    callme(callback)
except ZeroDivisionError:
    logger.exception("")
