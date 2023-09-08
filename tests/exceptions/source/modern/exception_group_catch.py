# fmt: off
import sys

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="", colorize=True, backtrace=False, diagnose=True)

x = ValueError


def a():
    try:
        raise ExceptionGroup("group", [ValueError(1)])
    except* x as e: raise ValueError(2)


def b():
    try:
        raise ExceptionGroup("group", [TypeError(1)])
    except* TypeError: a()


with logger.catch():
    b()
