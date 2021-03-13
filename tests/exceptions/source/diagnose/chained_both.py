import sys

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="", colorize=True, backtrace=False, diagnose=True)


def div(x, y):
    x / y


def cause(x, y):
    try:
        div(x, y)
    except Exception:
        raise ValueError("Division error")


def context(x, y):
    try:
        cause(x, y)
    except Exception as e:
        raise ValueError("Cause error") from e


try:
    context(1, 0)
except ValueError:
    logger.exception("")
