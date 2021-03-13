import sys

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="", diagnose=False, backtrace=False, colorize=False)
logger.add(sys.stderr, format="", diagnose=True, backtrace=False, colorize=False)
logger.add(sys.stderr, format="", diagnose=False, backtrace=True, colorize=False)
logger.add(sys.stderr, format="", diagnose=True, backtrace=True, colorize=False)


@logger.catch
def foo(a, b):
    yield a / b


f = foo(1, 0)

try:
    next(f)
except StopIteration:
    pass
