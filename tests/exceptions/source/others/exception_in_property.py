import sys

from loguru import logger

logger.remove()
logger.add(sys.stderr, format="", diagnose=True, backtrace=True, colorize=False)


class A:
    @property
    def value(self):
        try:
            1 / 0
        except:
            logger.opt(exception=True).debug("test")
            return None
        else:
            return "Never"


a = A()
value = a.value
