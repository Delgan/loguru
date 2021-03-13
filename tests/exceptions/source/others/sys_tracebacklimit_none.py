import sys

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="", diagnose=False, backtrace=False, colorize=False)
logger.add(sys.stderr, format="", diagnose=True, backtrace=False, colorize=False)
logger.add(sys.stderr, format="", diagnose=False, backtrace=True, colorize=False)
logger.add(sys.stderr, format="", diagnose=True, backtrace=True, colorize=False)


def a():
    b()


def b():
    c()


def c():
    d()


def d():
    e()


def e():
    f()


def f():
    g()


def g():
    h()


def h():
    i()


def i():
    j(1, 0)


def j(a, b):
    a / b


sys.tracebacklimit = None

try:
    a()
except ZeroDivisionError:
    logger.exception("")
