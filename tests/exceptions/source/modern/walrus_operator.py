# fmt: off
import sys

from loguru import logger


def foo():
    if a := "a" + (x:=1/0):
        pass


def bar():
    return [y for x in [1, 2] if (y := foo()) != 0]


@logger.catch
def main():
    walrus = False
    (walrus := foo())


logger.remove()
logger.add(sys.stderr, format="", diagnose=True, backtrace=True, colorize=True)

main()
