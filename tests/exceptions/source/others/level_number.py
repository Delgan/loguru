import sys

from loguru import logger

logger.remove()
logger.add(
    sys.stderr, format="{level.name} | {level.no}", diagnose=False, backtrace=False, colorize=False
)


def a():
    with logger.catch(level=13):
        1 / 0


a()
