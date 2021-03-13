import sys

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="", colorize=True, backtrace=False, diagnose=True)


def foo(abc, xyz):
    assert abc > 10 and xyz == 60


try:
    foo(9, 55)
except AssertionError:
    logger.exception("")
