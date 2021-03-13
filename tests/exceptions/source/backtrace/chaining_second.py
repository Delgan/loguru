import sys

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="", colorize=False, backtrace=True, diagnose=False)


def a_decorator():
    b_decorated()


def a_context_manager():
    with logger.catch():
        b_not_decorated()


def a_explicit():
    try:
        b_not_decorated()
    except ZeroDivisionError:
        logger.exception("")


@logger.catch()
def b_decorated():
    c()


def b_not_decorated():
    c()


def c():
    1 / 0


a_decorator()
a_context_manager()
a_explicit()
