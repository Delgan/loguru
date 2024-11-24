from loguru import logger

import sys


logger.remove()
logger.add(sys.stderr, format="", diagnose=False, backtrace=False, colorize=False)
logger.add(sys.stderr, format="", diagnose=False, backtrace=True, colorize=False)
logger.add(sys.stderr, format="", diagnose=False, backtrace=False, colorize=True)
logger.add(sys.stderr, format="", diagnose=True, backtrace=False, colorize=False)


def recursive(outer, inner):
    if outer == 0:
        raise ValueError("End of recursion")
    if inner == 0:
        recursive(outer=outer - 1, inner=outer - 1)
    recursive(outer=outer, inner=inner - 1)


try:
    recursive(10, 10)
except Exception:
    logger.exception("Oups")
