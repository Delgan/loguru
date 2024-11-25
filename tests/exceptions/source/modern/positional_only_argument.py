# fmt: off
import sys

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="", colorize=True, backtrace=False, diagnose=True)


def foo(a, /, b, *, c, **d): 1 / 0


def main():
    foo(1, 2, c=3)


with logger.catch():
    main()
