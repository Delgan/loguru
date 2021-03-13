import sys

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="", colorize=False, backtrace=True, diagnose=False)


def a_decorator():
    b_decorator()


def a_context_manager():
    b_context_manager()


def a_explicit():
    b_explicit()


def b_decorator():
    c_decorated()


def b_context_manager():
    with logger.catch():
        c_not_decorated()


def b_explicit():
    try:
        c_not_decorated()
    except ZeroDivisionError:
        logger.exception("")


@logger.catch
def c_decorated():
    1 / 0


def c_not_decorated():
    1 / 0


a_decorator()
a_context_manager()
a_explicit()
