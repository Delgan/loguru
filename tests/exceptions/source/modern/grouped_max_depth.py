from loguru import logger
import sys


@logger.catch
def main():
    nesting_left = ValueError("Left")
    for i in range(100):
        nesting_left = ExceptionGroup("group", [ValueError(-i), nesting_left])

    nesting_right = ValueError("Right")
    for i in range(100):
        nesting_right = ExceptionGroup("group", [nesting_right, ValueError(i)])

    nesting_both = ValueError("Both")
    for i in range(100):
        nesting_both = ExceptionGroup("group", [ValueError(-i), nesting_both, ValueError(i)])

    raise ExceptionGroup("group", [nesting_left, nesting_right, nesting_both])


logger.remove()
logger.add(sys.stderr, format="", diagnose=False, backtrace=False, colorize=False)
logger.add(sys.stderr, format="", diagnose=True, backtrace=True, colorize=True)

main()
