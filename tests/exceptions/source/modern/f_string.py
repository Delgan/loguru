# fmt: off
import sys

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="", colorize=True, backtrace=False, diagnose=True)


def hello():
    name = "world"
    f = 1
    f"{name}" and f'{{ {f / 0} }}'


with logger.catch():
    hello()
