# fmt: off
import sys
from typing import TypeVar, Union

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="", colorize=True, backtrace=False, diagnose=True)


T = TypeVar("T")
Name = str


def foo(a: int, b: Union[Name, float], c: "Name") -> T: 1 / 0


def main():
    bar: Name = foo(1, 2, 3)


with logger.catch():
    main()
