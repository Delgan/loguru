import sys

from loguru import logger

logger.remove()
logger.add(
    sys.stderr,
    format="{name} {file.name} {function} {line}",
    diagnose=False,
    backtrace=False,
    colorize=False,
)


def a():
    with logger.catch():
        1 / 0


a()
