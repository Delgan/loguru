# fmt: off
import sys
from typing import TypeVar, Union

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="", colorize=True, backtrace=False, diagnose=True)


T = TypeVar("T")
Name = str


def foo(a, /, b, *, c, **d): 1 / 0


def main():
    foo(1, 2, c=3)


with logger.catch():
    main()
