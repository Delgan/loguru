# fmt: off
from loguru import logger

import sys


logger.remove()
logger.add(sys.stderr, format="", diagnose=False, backtrace=False, colorize=False)
logger.add(sys.stderr, format="", diagnose=False, backtrace=True, colorize=False)
logger.add(sys.stderr, format="", diagnose=False, backtrace=False, colorize=True)
logger.add(sys.stderr, format="", diagnose=True, backtrace=False, colorize=False)

try:
    rec = lambda r, i: 1 / 0 if i == 0 else r(r, i - 1); rec(rec, 10)
except Exception:
    logger.exception("Error")
