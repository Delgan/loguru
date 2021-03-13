import sys

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="{message}", diagnose=False, backtrace=False, colorize=False)


@logger.catch(message="{record[name]} {record[file].name} {record[function]} {record[line]}")
def a():
    1 / 0


a()
