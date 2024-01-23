# fmt: off
import sys

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="", colorize=True, backtrace=False, diagnose=True)


def hello():
    output = f"Hello" + f' ' + f"""World""" and world()


def world():
    name = "world"
    f = 1
    f"{name} -> { f }" and {} or f'{{ {f / 0} }}'


with logger.catch():
    hello()
