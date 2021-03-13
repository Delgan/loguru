import sys
from collections import namedtuple

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="", colorize=False, backtrace=True, diagnose=False)


a, b = 1, 0


def div(x, y):
    x / y


def foo():
    div(a, b)


# See Twisted: https://git.io/fjJ48
# See Billiard: https://git.io/fjJ44
fake_code = namedtuple("fake_code", ("co_filename", "co_name"))
fake_frame = namedtuple("fake_frame", ("f_back", "f_code", "f_globals", "f_lineno", "f_locals"))
fake_traceback = namedtuple("fake_traceback", ("tb_frame", "tb_lasti", "tb_lineno", "tb_next"))


def make_fake(tb):
    if not tb:
        return None
    code = fake_code(tb.tb_frame.f_code.co_filename, tb.tb_frame.f_code.co_name)
    frame = fake_frame(None, code, {}, tb.tb_lineno, {})
    tb = fake_traceback(frame, tb.tb_lasti, tb.tb_lineno, make_fake(tb.tb_next))
    return tb


try:
    foo()
except ZeroDivisionError:
    type_, value, tb = sys.exc_info()
    tb = make_fake(tb)
    logger.opt(exception=(type_, value, tb)).error("")
