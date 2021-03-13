import sys

from loguru import logger

# fmt: off

logger.remove()
logger.add(sys.stderr, format="", colorize=True, backtrace=False, diagnose=True)


class Obj:
    @property
    def forbidden(self):
        raise RuntimeError


a = Obj()
a.b = "123"


def foo():
    x = None
    ... + 1 + bar(a).b + a.forbidden + a.nope.a + x.__bool__ or a. b . isdigit() and .3 + ...


try:
    foo()
except TypeError:
    logger.exception("")
