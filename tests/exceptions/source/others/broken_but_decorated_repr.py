import sys

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="", diagnose=True, backtrace=True, colorize=False, catch=True)


class Foo:
    @logger.catch(reraise=True)
    def __repr__(self):
        raise ValueError("Something went wrong (Foo)")


class Bar:
    def __repr__(self):
        with logger.catch(reraise=True):
            raise ValueError("Something went wrong (Bar)")


foo = Foo()
bar = Bar()

try:
    repr(foo)
except ValueError:
    pass


try:
    repr(bar)
except ValueError:
    pass
