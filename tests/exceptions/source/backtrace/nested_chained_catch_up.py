import sys

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="", colorize=False, backtrace=False, diagnose=False)
logger.add(sys.stderr, format="", colorize=False, backtrace=True, diagnose=False)


def foo():
    bar()


@logger.catch(ValueError)
def bar():
    1 / 0


@logger.catch
def main():
    try:
        foo()
    except Exception as e:
        raise ZeroDivisionError from e


main()
