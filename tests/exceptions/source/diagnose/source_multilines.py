import sys

from loguru import logger

# fmt: off

logger.remove()
logger.add(sys.stderr, format="", colorize=True, backtrace=False, diagnose=True)


def bug_1(n):
    return ("""multi-lines
""" + n / 0)


def bug_2(a, b, c):
    return (1 / 0 + a + b + \
            c)


def bug_3(string):
    return min(10
           , string, 20 / 0)


def bug_4():
    a, b = 1, 0
    dct = {
        "foo": 1,
        "bar": a / b,
    }
    return dct


string = """multi-lines
"""


try:
    bug_1(10)
except ZeroDivisionError:
    logger.exception("")


try:
    bug_2(1, string, 3)
except ZeroDivisionError:
    logger.exception("")


try:
    bug_3(string)
except ZeroDivisionError:
    logger.exception("")


try:
    bug_4()
except ZeroDivisionError:
    logger.exception("")
