import sys

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="", diagnose=False, backtrace=False, colorize=False)
logger.add(sys.stderr, format="", diagnose=True, backtrace=False, colorize=False)
logger.add(sys.stderr, format="", diagnose=False, backtrace=True, colorize=False)
logger.add(sys.stderr, format="", diagnose=True, backtrace=True, colorize=False)


@logger.catch
async def foo(a, b):
    yield a
    yield b


gen = foo(1, 0)

op = gen.asend(None)
try:
    op.send(None)
except StopIteration:
    pass

op = gen.athrow(ValueError("Bug"))
try:
    op.send(None)
except StopAsyncIteration:
    pass
