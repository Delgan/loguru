from loguru import logger
import sys


def divide_by_zero():
    1 / 0


def raise_value_error(value):
    raise ValueError(value)


@logger.catch
def main():
    try:
        try:
            divide_by_zero()
        except Exception as err:
            error_1 = err

        try:
            raise_value_error(100)
        except Exception as err:
            error_2 = err

        raise ExceptionGroup("group_1", [error_1, error_2])
    except ExceptionGroup as error_3:
        try:
            raise_value_error(-100)
        except Exception as err:
            error_4 = err

        raise ExceptionGroup("group_2", [error_4, error_3]) from None


logger.remove()
logger.add(sys.stderr, format="", diagnose=False, backtrace=False, colorize=False)
logger.add(sys.stderr, format="", diagnose=True, backtrace=True, colorize=True)

main()
