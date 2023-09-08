import sys

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="", diagnose=True, backtrace=True, colorize=False)


def a():
    x = 1
    y = 0
    x / y


def b():
    a()


def c(f):
    f()


@logger.catch
def main():
    try:
        c(b)
    except Exception as error_1:
        try:
            c(a)
        except Exception as error_2:
            try:
                a()
            except Exception as error_3:
                raise ExceptionGroup("group", [error_1, error_2, error_3]) from None


logger.remove()
logger.add(sys.stderr, format="", diagnose=False, backtrace=False, colorize=False)
logger.add(sys.stderr, format="", diagnose=True, backtrace=True, colorize=True)

main()
