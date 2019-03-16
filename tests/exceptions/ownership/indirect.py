import os, site, sys
from usersite.lib import divide_indirect
from loguru import logger

site.USER_SITE = os.path.abspath(os.path.join(os.path.dirname(__file__), "usersite"))
logger.remove()
logger.add(sys.stderr, format="", colorize=True, backtrace=True, diagnose=True)

try:
    divide_indirect(10, 0)
except ZeroDivisionError:
    logger.exception("")

