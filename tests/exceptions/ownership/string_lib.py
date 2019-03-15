import os, site, sys
from usersite.lib import execute
from loguru import logger

site.USER_SITE = os.path.abspath(os.path.join(os.path.dirname(__file__), "usersite"))
logger.remove()
logger.add(sys.stderr, format="", colorize=True, backtrace=True)

try:
    execute()
except ZeroDivisionError:
    logger.exception("")

