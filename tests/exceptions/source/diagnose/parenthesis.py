import sys

from loguru import logger

# fmt: off

logger.remove()
logger.add(sys.stderr, format="", colorize=True, backtrace=False, diagnose=True)


class XYZ:
    pass


def a(b, c):
    x = XYZ()
    x.val = 9
    (a, b, x.val, ) = 12, 15 / c, 17


def b():
    foo, bar, baz = {}, XYZ, 0
    foo[("baz")] = bar() + (a(5, baz))


def c():
    x = XYZ()
    x.val = 123
    x.val += 456 and b()


def d(j):
    x, y, z = 2, 5, 3
    xyz = XYZ()
    xyz.val = 123
    i = 12 \
        ; z = (x * y); y = (j or xyz.val * c() \
            + 3)


def e():
    a = 1
    (5 \
        ) + d(()) + a


with logger.catch():
    e()
