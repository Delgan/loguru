import sys
from collections import namedtuple

from loguru import logger


logger.remove()
logger.add(
    sys.stderr,
    format="{line}: {message}",
    colorize=False,
    backtrace=True,
    diagnose=False,
)

# Regression since CPython 3.10: the `lineno` can be `None`: https://github.com/python/cpython/issues/89726
fake_code = namedtuple("fake_code", ("co_filename", "co_name"))
fake_frame = namedtuple("fake_frame", ("f_back", "f_code", "f_globals", "f_lineno", "f_locals"))
fake_traceback = namedtuple("fake_traceback", ("tb_frame", "tb_lasti", "tb_lineno", "tb_next"))


def make_fake(tb):
    if not tb:
        return None
    code = fake_code(tb.tb_frame.f_code.co_filename, tb.tb_frame.f_code.co_name)
    frame = fake_frame(None, code, {}, None, {})
    tb = fake_traceback(frame, tb.tb_lasti, None, make_fake(tb.tb_next))
    return tb


def a():
    1 / 0


def b():
    a()


try:
    b()
except Exception as e:
    type_, value, tb = sys.exc_info()
    tb = make_fake(tb)
    logger.opt(exception=(type_, value, tb)).error("An error occurred")
