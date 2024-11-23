from loguru import logger

import sys

sys.setrecursionlimit(1000)

logger.remove()
logger.add(sys.stderr, format="", diagnose=False, backtrace=False, colorize=False)
logger.add(sys.stderr, format="", diagnose=False, backtrace=True, colorize=False)
logger.add(sys.stderr, format="", diagnose=False, backtrace=False, colorize=True)
logger.add(sys.stderr, format="", diagnose=True, backtrace=False, colorize=False)


def recursive():
    recursive()


try:
    recursive()
except Exception:
    logger.exception("Oups")
