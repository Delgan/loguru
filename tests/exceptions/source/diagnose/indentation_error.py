import sys

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="", colorize=True, backtrace=False, diagnose=True)


code = """
if True:
    a = 5
        print("foobar")  #intentional faulty indentation here.
    b = 7
"""

try:
    exec(code)
except IndentationError:
    logger.exception("")
