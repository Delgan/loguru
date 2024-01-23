# fmt: off
import sys

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="", colorize=True, backtrace=False, diagnose=True)

def case(x):
    y = 1
    match y / 0:
        case 1:
            pass

def match(x):
    y = 1
    match x:
        case y: case(x)

with logger.catch():
    match(1)
