import sys

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="", colorize=False, backtrace=True, diagnose=False)


@logger.catch()
def a_decorated():
    try:
        1 / 0
    except ZeroDivisionError:
        raise ValueError("NOK")


def a_not_decorated():
    try:
        1 / 0
    except ZeroDivisionError:
        raise ValueError("NOK")


def b_decorator():
    a_decorated()


def b_context_manager():
    with logger.catch():
        a_not_decorated()


def b_explicit():
    try:
        a_not_decorated()
    except ValueError:
        logger.exception("")


b_decorator()
b_context_manager()
b_explicit()
