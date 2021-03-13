import sys

from loguru import logger

# fmt: off

logger.remove()
logger.add(sys.stderr, format="", colorize=True, backtrace=False, diagnose=True)


def a():
    1 / 0 + 1 * 0 - 1 % 0 // 1**0 @ 1  # Error


def b():
    a() or False == None != True


def c():
    1, 2.5, 3.0, 0.4, "str", r"rrr", rb"binary", b()


def d():
    min(range(1, 10)), list(), dict(), c(), ...


def e(x):
    x in [1], x in (1,), x in {1}, x in {1: 1}, d()


try:
    e(0)
except ZeroDivisionError:
    logger.exception("")
