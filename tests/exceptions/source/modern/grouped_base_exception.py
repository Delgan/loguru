import asyncio
import sys

from loguru import logger


@logger.catch(BaseExceptionGroup)
def main():
    errors = [ValueError("data failed"), asyncio.CancelledError("worker stopped")]
    raise BaseExceptionGroup("mixed failures", errors)


logger.remove()
logger.add(sys.stderr, format="", diagnose=False, backtrace=False, colorize=False)
logger.add(sys.stderr, format="", diagnose=True, backtrace=True, colorize=True)

main()
