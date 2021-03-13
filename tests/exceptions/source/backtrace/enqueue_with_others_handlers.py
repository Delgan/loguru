import sys

from loguru import logger


def check_tb_sink(message):
    exception = message.record["exception"]
    if exception is None:
        return
    assert exception.traceback is not None


logger.remove()

logger.add(
    check_tb_sink, enqueue=False, catch=False, colorize=False, backtrace=True, diagnose=False
)
logger.add(
    sys.stderr, format="", enqueue=True, catch=False, colorize=False, backtrace=True, diagnose=False
)
logger.add(
    check_tb_sink, enqueue=False, catch=False, colorize=False, backtrace=True, diagnose=False
)

try:
    1 / 0
except ZeroDivisionError:
    logger.exception("Error")
