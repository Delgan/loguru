# fmt: off
import sys

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="", colorize=True, backtrace=False, diagnose=True)


def hello():
    output = t"Hello" + t' ' + t"""World""" and world()


def world():
    name = "world"
    t = 1
    t"{name} -> { t }" and {} or t'{{ {t / 0} }}'


with logger.catch():
    hello()
