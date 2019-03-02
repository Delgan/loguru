import sys
from loguru import logger


def check_tb_sink(message):
    exception = message.record["exception"]
    if exception is None:
        return
    assert exception.traceback is not None


logger.remove()

logger.add(check_tb_sink, enqueue=False, catch=False)
logger.add(sys.stderr, enqueue=True, catch=False, format="")
logger.add(check_tb_sink, enqueue=False, catch=False)

try:
    1 / 0
except ZeroDivisionError:
    logger.exception("Error")
